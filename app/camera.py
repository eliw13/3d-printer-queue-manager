"""Snapshot grabber for the P1/A1-series camera (port 6000).

These printers don't offer RTSP. Instead, a TLS socket on port 6000 sends a
stream of JPEG frames after an 80-byte login packet. Each frame has a 16-byte
header whose first 4 bytes (little-endian) give the JPEG size.

We connect, read one frame, and disconnect. A short cache stops several
browser tabs from opening several connections at once.
"""

from __future__ import annotations

import socket
import ssl
import struct
import threading
import time

CAMERA_PORT = 6000
CACHE_SECONDS = 2.0
MAX_FRAME_BYTES = 5_000_000


class CameraError(RuntimeError):
    pass


def _recv_exact(sock: ssl.SSLSocket, size: int) -> bytes:
    buf = bytearray()
    while len(buf) < size:
        chunk = sock.recv(size - len(buf))
        if not chunk:
            raise CameraError("Camera closed the connection")
        buf.extend(chunk)
    return bytes(buf)


def _auth_packet(access_code: str) -> bytes:
    header = struct.pack("<IIII", 0x40, 0x3000, 0, 0)
    user = b"bblp".ljust(32, b"\x00")
    code = access_code.encode("ascii").ljust(32, b"\x00")
    return header + user + code


def grab_frame(ip: str, access_code: str, timeout: float = 10.0) -> bytes:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # printer uses a self-signed certificate
    try:
        with socket.create_connection((ip, CAMERA_PORT), timeout=timeout) as raw:
            with ctx.wrap_socket(raw, server_hostname=ip) as sock:
                sock.sendall(_auth_packet(access_code))
                header = _recv_exact(sock, 16)
                size = struct.unpack("<I", header[:4])[0]
                if not 0 < size <= MAX_FRAME_BYTES:
                    raise CameraError(f"Unexpected frame size {size}; is the access code right?")
                jpeg = _recv_exact(sock, size)
    except (OSError, ssl.SSLError) as exc:
        raise CameraError(f"Could not reach camera at {ip}:{CAMERA_PORT}: {exc}") from exc
    if not (jpeg.startswith(b"\xff\xd8") and jpeg.endswith(b"\xff\xd9")):
        raise CameraError("Camera sent data that isn't a JPEG")
    return jpeg


class Camera:
    def __init__(self, ip: str, access_code: str) -> None:
        self.ip = ip
        self.access_code = access_code
        self._lock = threading.Lock()
        self._frame: bytes | None = None
        self._taken_at = 0.0

    def snapshot(self) -> tuple[bytes, float]:
        with self._lock:
            if self._frame is None or time.time() - self._taken_at > CACHE_SECONDS:
                self._frame = grab_frame(self.ip, self.access_code)
                self._taken_at = time.time()
            return self._frame, self._taken_at
