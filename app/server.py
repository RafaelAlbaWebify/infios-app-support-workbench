from __future__ import annotations

import os
import threading
import webbrowser
from pathlib import Path

import uvicorn


def run_workbench_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    open_browser: bool = True,
    database_path: Path | None = None,
) -> None:
    """Run the local INFIOS workbench with safe local-only defaults."""
    if database_path is not None:
        database_path = database_path.expanduser().resolve()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        os.environ["INFIOS_DB_PATH"] = str(database_path)

    url_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    url = f"http://{url_host}:{port}"

    if open_browser:
        timer = threading.Timer(0.8, webbrowser.open, args=(url,))
        timer.daemon = True
        timer.start()

    print(f"INFIOS workbench: {url}")
    print("Press Ctrl+C to stop the local server.")
    uvicorn.run("app.main:app", host=host, port=port, log_level="info")
