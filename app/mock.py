"""Fake printer and camera for trying the dashboard without a printer."""

from __future__ import annotations

import time

from .printer import summarize

_START = time.time()
_JOB_SECONDS = 600

SNAPSHOT_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 640 480">
<rect width="640" height="480" fill="#1f2428"/>
<rect x="170" y="330" width="300" height="20" rx="3" fill="#3a4148"/>
<rect x="260" y="240" width="120" height="90" rx="6" fill="#4f9d69"/>
<text x="320" y="420" fill="#9aa4ad" font-family="sans-serif" font-size="20" text-anchor="middle">Mock camera (PRINTER_MOCK=true)</text>
</svg>"""


class MockPrinter:
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def status(self) -> dict:
        elapsed = (time.time() - _START) % _JOB_SECONDS
        pct = int(elapsed / _JOB_SECONDS * 100)
        raw = {
            "print": {
                "gcode_state": "RUNNING",
                "subtask_name": "Benchy (mock)",
                "mc_percent": pct,
                "mc_remaining_time": int((_JOB_SECONDS - elapsed) / 60),
                "layer_num": int(pct * 2.4),
                "total_layer_num": 240,
                "nozzle_temper": 219.6,
                "nozzle_target_temper": 220,
                "bed_temper": 54.8,
                "bed_target_temper": 55,
                "spd_lvl": 2,
                "wifi_signal": "-48dBm",
                "lights_report": [{"node": "chamber_light", "mode": "on"}],
                "ams": {"ams": [{"id": "0", "tray": [
                    {"id": "0", "tray_type": "PLA", "tray_color": "FFFFFFFF", "remain": 80},
                    {"id": "1", "tray_type": "PLA", "tray_color": "161616FF", "remain": 45},
                    {"id": "2", "tray_type": "PETG", "tray_color": "D62D2DFF", "remain": 100},
                ]}]},
            }
        }
        return summarize(raw, connected=True, last_message_at=time.time())


class MockCamera:
    media_type = "image/svg+xml"

    def snapshot(self) -> tuple[bytes, float]:
        return SNAPSHOT_SVG, time.time()
