from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import pytest
from playwright.sync_api import Page, Route, expect


@pytest.fixture(scope="module")
def handover_base_url() -> str:
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
            raise RuntimeError("Handover UI server did not become healthy.")
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def test_handover_list_and_detail(page: Page, handover_base_url: str) -> None:
    handover = {
        "handover_id": "handover-1",
        "shift_label": "Evening shift",
        "prepared_by": "L2 Support",
        "summary": "Two incidents require follow-up.",
        "created_at": "2026-07-16T14:00:00Z",
        "cases": [
            {"case_id": "case-100", "status_summary": "Evidence collection is complete.", "next_action": "Review the linked application logs.", "blocker": "Waiting for the application owner.", "attention_required": True},
            {"case_id": "case-101", "status_summary": "User impact has stopped.", "next_action": "Confirm the monitoring result.", "blocker": None, "attention_required": False},
        ],
    }

    def api(route: Route) -> None:
        if route.request.url.endswith("/api/handovers?limit=100"):
            route.fulfill(json={"handovers": [handover], "count": 1})
        elif route.request.url.endswith("/api/handovers/handover-1"):
            route.fulfill(json=handover)
        else:
            route.continue_()

    page.route("**/api/handovers**", api)
    page.goto(f"{handover_base_url}/handovers")
    expect(page.get_by_role("heading", name="Evening shift")).to_be_visible()
    expect(page.get_by_text("Two incidents require follow-up.")).to_be_visible()
    expect(page.get_by_role("heading", name="case-100")).to_be_visible()
    expect(page.get_by_text("Constraint: Waiting for the application owner.")).to_be_visible()
    expect(page.get_by_text("Attention required", exact=True)).to_be_visible()
    expect(page.get_by_text("They do not independently prove incident severity", exact=False)).to_be_visible()
    Path("browser-artifacts").mkdir(exist_ok=True)
    page.screenshot(path="browser-artifacts/shift-handover-ui.png", full_page=True)


def test_handover_empty_and_error_states(page: Page, handover_base_url: str) -> None:
    page.route("**/api/handovers?limit=100", lambda route: route.fulfill(json={"handovers": [], "count": 0}))
    page.goto(f"{handover_base_url}/handovers")
    expect(page.get_by_text("No shift handovers are currently stored.")).to_be_visible()
    page.unroute("**/api/handovers?limit=100")
    page.route("**/api/handovers?limit=100", lambda route: route.fulfill(status=500, json={"detail": "Storage unavailable"}))
    page.reload()
    expect(page.get_by_role("alert")).to_contain_text("Storage unavailable")
