"""Settings loaded from environment variables / a local .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    printer_ip: str
    access_code: str
    serial: str
    host: str
    port: int
    mock: bool

    def missing(self) -> list[str]:
        """Names of required settings that are empty (ignored in mock mode)."""
        if self.mock:
            return []
        required = {
            "PRINTER_IP": self.printer_ip,
            "PRINTER_ACCESS_CODE": self.access_code,
            "PRINTER_SERIAL": self.serial,
        }
        return [name for name, value in required.items() if not value]


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        printer_ip=os.getenv("PRINTER_IP", "").strip(),
        access_code=os.getenv("PRINTER_ACCESS_CODE", "").strip(),
        serial=os.getenv("PRINTER_SERIAL", "").strip().upper(),
        host=os.getenv("APP_HOST", "127.0.0.1").strip(),
        port=int(os.getenv("APP_PORT", "8000")),
        mock=_bool(os.getenv("PRINTER_MOCK")),
    )
