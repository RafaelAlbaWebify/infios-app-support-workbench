from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="module")
def analytics_base_url() -> str:
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
            raise RuntimeError("Analytics browser server did not become healthy.")
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def test_operator_can_open_refresh_and_change_window(page: Page, analytics_base_url: str) -> None:
    page.goto(f"{analytics_base_url}/analytics")

    expect(page.get_by_role("heading", name="Support analytics")).to_be_visible()
    expect(page.get_by_text("Recorded activity trends")).to_be_visible()
    expect(page.get_by_text("Separate attention signals")).to_be_visible()
    expect(page.get_by_role("link", name="Incident workbench")).to_have_attribute("href", "/")
    expect(page.locator("#analytics-error")).to_be_hidden()
    expect(page.locator("#analytics-status")).to_contain_text("30-day activity window")
    expect(page.locator("#trend-window-label")).to_have_text("30 days")

    page.locator("#analytics-window").select_option("7")
    expect(page.locator("#analytics-status")).to_contain_text("7-day activity window")
    expect(page.locator("#trend-window-label")).to_have_text("7 days")

    page.get_by_role("button", name="Refresh reports").click()
    expect(page.locator("#analytics-status")).to_contain_text("Reports refreshed")

    artifact_dir = Path("browser-artifacts")
    artifact_dir.mkdir(exist_ok=True)
    page.screenshot(path=str(artifact_dir / "analytics-ui-time-window.png"), full_page=True)
