from __future__ import annotations

import socket
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest
from playwright.sync_api import Page


@pytest.fixture(scope="module")
def incident_density_base_url() -> str:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(80):
            try:
                with urlopen(f"{base_url}/api/health", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("Incident density test server did not become healthy.")
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def test_incident_workbench_uses_compact_components(page: Page, incident_density_base_url: str) -> None:
    page.set_viewport_size({"width": 1440, "height": 1000})
    response = page.goto(f"{incident_density_base_url}/")
    assert response is not None and response.status == 200

    values = page.evaluate(
        """() => {
          const panel = document.querySelector('.infios-app-content .panel');
          const heading = panel.querySelector('h2');
          const sidebar = document.querySelector('.infios-app-content .sidebar');
          return {
            panelPadding: parseFloat(getComputedStyle(panel).paddingTop),
            panelRadius: parseFloat(getComputedStyle(panel).borderTopLeftRadius),
            headingSize: parseFloat(getComputedStyle(heading).fontSize),
            sidebarPadding: parseFloat(getComputedStyle(sidebar).paddingTop),
          };
        }"""
    )
    assert values["panelPadding"] <= 18
    assert values["panelRadius"] <= 12
    assert values["headingSize"] <= 25
    assert values["sidebarPadding"] <= 16

    page.set_viewport_size({"width": 390, "height": 844})
    page.reload()
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 1
