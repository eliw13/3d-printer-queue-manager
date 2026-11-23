"""Read-only connection to a Bambu Lab printer's local MQTT broker (LAN mode).

The printer runs an MQTT broker on port 8883 with a self-signed certificate.
We log in as user "bblp" with the LAN access code, subscribe to
device/<serial>/report and merge the JSON reports into one state dict.

The only thing ever published is a "pushall" request, which asks the printer
to send its full current state. It does not move, heat or start anything.
P1-series printers otherwise send only the fields that changed, so we do a
pushall on connect and rarely after that (Bambu advises against frequent ones).
"""

from __future__ import annotations

import json
import logging
import ssl
import threading
import time
from typing import Any

import paho.mqtt.client as mqtt

log = logging.getLogger(__name__)

MQTT_PORT = 8883
PUSHALL_INTERVAL_S = 300  # P1 series: don't request full state more often than this


def deep_merge(target: dict[str, Any], update: dict[str, Any]) -> None:
    """Merge a partial report into the stored state, in place."""
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_merge(target[key], value)
        else:
            target[key] = value


class PrinterClient:
    def __init__(self, ip: str, access_code: str, serial: str) -> None:
        self.ip = ip
        self.serial = serial
        self._state: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._connected = False
        self._last_message_at: float | None = None
        self._last_pushall_at = 0.0
        self._last_error: str | None = None

        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"queue-manager-{int(time.time())}",
        )
        self._client.username_pw_set("bblp", access_code)
        # The printer uses a self-signed certificate.
        self._client.tls_set(cert_reqs=ssl.CERT_NONE)
        self._client.tls_insecure_set(True)
        self._client.reconnect_delay_set(min_delay=2, max_delay=30)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    # --- lifecycle -------------------------------------------------------
    def start(self) -> None:
        log.info("Connecting to printer MQTT at %s:%s", self.ip, MQTT_PORT)
        self._client.connect_async(self.ip, MQTT_PORT, keepalive=60)
        self._client.loop_start()

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    # --- callbacks -------------------------------------------------------
    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            self._last_error = f"MQTT connect refused: {reason_code}"
            log.warning(self._last_error)
            return
        self._connected = True
        self._last_error = None
        log.info("Connected to printer; subscribing to reports")
        client.subscribe(f"device/{self.serial}/report")
        self._request_pushall(force=True)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        self._connected = False
        if reason_code.is_failure:
            self._last_error = f"Disconnected: {reason_code}"
            log.warning(self._last_error)

    def _on_message(self, client, userdata, msg) -> None:
        try:
            payload = json.loads(msg.payload)
        except ValueError:
            return
        with self._lock:
            deep_merge(self._state, payload)
            self._last_message_at = time.time()

    # --- requests (read-only) -------------------------------------------
    def _request_pushall(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self._last_pushall_at < PUSHALL_INTERVAL_S:
            return
        self._last_pushall_at = now
        request = {"pushing": {"sequence_id": "0", "command": "pushall"}}
        self._client.publish(f"device/{self.serial}/request", json.dumps(request))

    # --- public ----------------------------------------------------------
    def status(self) -> dict[str, Any]:
        self._request_pushall()
        with self._lock:
            raw = json.loads(json.dumps(self._state))  # cheap deep copy
            last = self._last_message_at
        return summarize(raw, connected=self._connected, last_message_at=last, error=self._last_error)


def summarize(
    raw: dict[str, Any],
    *,
    connected: bool,
    last_message_at: float | None,
    error: str | None = None,
) -> dict[str, Any]:
    """Turn the printer's raw report into the fields the dashboard shows."""
    p = raw.get("print", {})

    def num(key: str) -> float | None:
        value = p.get(key)
        try:
            return round(float(value), 1)
        except (TypeError, ValueError):
            return None

    ams_trays = []
    for unit in (p.get("ams") or {}).get("ams", []) or []:
        for tray in unit.get("tray", []) or []:
            if not tray.get("tray_type"):
                continue
            ams_trays.append(
                {
                    "slot": f"{int(unit.get('id', 0)) + 1}-{int(tray.get('id', 0)) + 1}",
                    "type": tray.get("tray_type"),
                    "color": "#" + str(tray.get("tray_color", "FFFFFFFF"))[:6],
                    "remaining": tray.get("remain"),
                }
            )

    lights = {l.get("node"): l.get("mode") for l in p.get("lights_report", []) or []}

    return {
        "connected": connected,
        "last_update": last_message_at,
        "error": error,
        "state": p.get("gcode_state") or "UNKNOWN",
        "job_name": p.get("subtask_name") or p.get("gcode_file") or None,
        "progress": p.get("mc_percent"),
        "remaining_minutes": p.get("mc_remaining_time"),
        "layer": p.get("layer_num"),
        "total_layers": p.get("total_layer_num"),
        "nozzle_temp": num("nozzle_temper"),
        "nozzle_target": num("nozzle_target_temper"),
        "bed_temp": num("bed_temper"),
        "bed_target": num("bed_target_temper"),
        "speed_level": p.get("spd_lvl"),
        "wifi_signal": p.get("wifi_signal"),
        "chamber_light": lights.get("chamber_light"),
        "print_error": p.get("print_error") or 0,
        "ams": ams_trays,
    }
