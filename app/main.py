"""FastAPI app: status API, camera snapshot and the dashboard page."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .camera import Camera, CameraError
from .config import load_settings
from .mock import MockCamera, MockPrinter
from .printer import PrinterClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")

STATIC = Path(__file__).parent / "static"
settings = load_settings()

if settings.mock:
    printer = MockPrinter()
    camera = MockCamera()
else:
    missing = settings.missing()
    if missing:
        raise SystemExit(
            f"Missing settings: {', '.join(missing)}. Copy .env.example to .env and fill them in."
        )
    printer = PrinterClient(settings.printer_ip, settings.access_code, settings.serial)
    camera = Camera(settings.printer_ip, settings.access_code)


@asynccontextmanager
async def lifespan(_: FastAPI):
    printer.start()
    yield
    printer.stop()


app = FastAPI(title="3D Printer Queue Manager", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/status")
def status() -> dict:
    return {"mock": settings.mock, **printer.status()}


@app.get("/api/snapshot")
async def snapshot() -> Response:
    try:
        data, taken_at = await run_in_threadpool(camera.snapshot)
    except CameraError as exc:
        log.warning("Snapshot failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    media_type = getattr(camera, "media_type", "image/jpeg")
    return Response(
        content=data,
        media_type=media_type,
        headers={"Cache-Control": "no-store", "X-Taken-At": f"{taken_at:.3f}"},
    )
