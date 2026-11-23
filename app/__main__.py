"""Run with: python -m app"""

import uvicorn

from .config import load_settings

if __name__ == "__main__":
    s = load_settings()
    print(f"Dashboard: http://{'localhost' if s.host in ('127.0.0.1', '0.0.0.0') else s.host}:{s.port}")
    uvicorn.run("app.main:app", host=s.host, port=s.port)
