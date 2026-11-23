# 3D Printer Queue Manager

A local web dashboard for a Bambu Lab P1S, talking to the printer directly over
your home network (LAN mode). No Bambu cloud involved.

**Step 1 (this version):** live job status, temperatures, filament and camera
snapshots. It is **read-only**: it never starts, pauses, heats or moves anything.

Coming next: upload and queue sliced files with a preview, paste a MakerWorld
link to import a model, and in-app slicing.

## Setup on Windows

1. Install **Python 3.11 or newer** from [python.org](https://www.python.org/downloads/).
   During install, tick **"Add python.exe to PATH"**.
2. Pull this repo with GitHub Desktop (e.g. into `C:\Git\3d-printer-queue-manager`).
3. In that folder, copy `.env.example` to a new file named `.env` and fill in:
   - `PRINTER_IP`: on the printer, **Settings → Network**
   - `PRINTER_ACCESS_CODE`: same screen
   - `PRINTER_SERIAL`: **Settings → Device**, or in Bambu Handy

   `.env` is ignored by Git, so your access code stays on your PC.
4. Double-click **`start.bat`**. The first run installs what it needs (about a minute).
5. Open **http://localhost:8000** in your browser.

To try the dashboard without the printer, set `PRINTER_MOCK=true` in `.env`.

### Seeing it from your phone (same Wi-Fi)

Set `APP_HOST=0.0.0.0` in `.env`, restart, and open `http://<your-PC's-IP>:8000`
on your phone. Windows may ask to allow Python through the firewall; allow it on
**private networks** only.

## Printer requirements

- The printer and PC must be on the same network.
- **LAN-only mode is not required.** The P1S serves its local MQTT and camera
  feeds while connected to the Bambu cloud too, so Bambu Handy keeps working.
  If the dashboard can't connect, check that **LAN Mode Liveview** is on under
  the printer's network settings.
- Newer Bambu firmware limits *control* commands from third-party apps unless
  the printer is in LAN mode with **Developer Mode** on. Reading status and the
  camera, which is all this version does, works without it. Starting queued
  prints (step 2) may need it.

## How it works

| Feature  | Printer port | Protocol |
|----------|-------------:|----------|
| Status   | 8883 | MQTT over TLS, user `bblp` + access code. Subscribes to `device/<serial>/report`. The only message sent is `pushall`, which asks for the full current state. |
| Camera   | 6000 | TLS socket that streams JPEG frames after a login packet. The app grabs one frame per snapshot and disconnects. |

Code layout:

```
app/
  main.py      FastAPI routes: /, /api/status, /api/snapshot
  printer.py   MQTT client and status summary
  camera.py    P1S camera snapshot grabber
  mock.py      Fake printer for PRINTER_MOCK=true
  config.py    Settings from .env
  static/      Dashboard (plain HTML/CSS/JS, no build step)
```

Run manually (any OS):

```
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m app
```
