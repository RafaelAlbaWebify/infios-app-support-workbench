from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "http://127.0.0.1:8765"
SCREENSHOT_DIR = Path("browser-artifacts/screenshots")


@pytest.fixture(scope="session", autouse=True)
def live_server() -> None:
    Path("browser-artifacts").mkdir(exist_ok=True)
    env = os.environ.copy()
    env["INFIOS_DB_PATH"] = str(Path("browser-artifacts/browser-tests.sqlite3").resolve())
    process = subprocess.Popen(
        [
            "python",
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8765",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"INFIOS server stopped before browser tests:\n{output}")
        try:
            if httpx.get(f"{BASE_URL}/api/health", timeout=0.5).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.2)
    else:
        process.terminate()
        raise RuntimeError("INFIOS server did not become ready for browser tests")

    yield

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def _capture(page: Page, name: str) -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SCREENSHOT_DIR / name), full_page=True)


def test_first_time_l1_workflow_is_usable(page: Page) -> None:
    page.goto(BASE_URL)
    expect(page.get_by_role("heading", name="Recent incidents")).to_be_visible()
    expect(page.get_by_text("Unknown is valid")).to_be_visible()

    page.get_by_role("button", name="New incident").click()
    page.get_by_label("Application or service").fill("Order Management")
    page.get_by_label("Short problem description").fill("Orders page fails after login")
    page.get_by_label("Who is affected?").select_option(label="Several users")
    page.get_by_label("Business impact").select_option(label="Important function unavailable")
    page.get_by_role("button", name="Create incident and continue").click()

    expect(
        page.get_by_role("heading", name=re.compile(r"Orders page fails after login", re.I))
    ).to_be_visible()
    expect(page.get_by_role("heading", name="Evidence collected")).to_be_visible()
    expect(page.get_by_role("heading", name="Safe guided checks")).to_be_visible()
    expect(page.get_by_role("heading", name="Review and escalate")).to_be_visible()
    expect(page.locator("#action-result-editor")).to_be_hidden()
    _capture(page, "desktop-new-case.png")


def test_evidence_observation_and_timeline_workflow(page: Page) -> None:
    page.goto(BASE_URL)
    page.get_by_role("button", name="New incident").click()
    page.get_by_label("Application or service").fill("Order Management")
    page.get_by_label("Short problem description").fill("Orders API returns 500")
    page.get_by_role("button", name="Create incident and continue").click()

    page.get_by_role("button", name="HTTP/API evidence").click()
    page.get_by_label("Source", exact=True).fill("Browser developer tools")
    page.get_by_label("What did you observe?").fill("POST /api/orders returned HTTP 500")
    page.get_by_label("How certain is this information?").select_option("technically_confirmed")
    page.get_by_role("button", name="Save evidence").click()

    expect(page.get_by_text("POST /api/orders returned HTTP 500")).to_be_visible()
    page.get_by_label("Factual statement").fill("HTTP 500 was observed on /api/orders.")
    page.locator("#observation-evidence").select_option(index=0)
    page.get_by_role("button", name="Save observation").click()

    expect(
        page.locator("#observation-list").get_by_text(
            "HTTP 500 was observed on /api/orders.", exact=True
        )
    ).to_be_visible()
    expect(
        page.locator("#timeline-list").get_by_text("case created", exact=True)
    ).to_be_visible()
    expect(
        page.locator("#timeline-list").get_by_text("observation", exact=True)
    ).to_be_visible()
    _capture(page, "desktop-observation-timeline.png")


def test_mobile_layout_has_no_horizontal_overflow(page: Page) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(BASE_URL)
    expect(page.get_by_role("heading", name="Recent incidents")).to_be_visible()

    overflow = page.evaluate(
        "document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert overflow is False
    _capture(page, "mobile-dashboard.png")


def test_basic_accessibility_contract(page: Page) -> None:
    page.goto(BASE_URL)
    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page.get_by_role("main")).to_be_visible()
    expect(page.locator("button:not([type])")).to_have_count(0)

    page.get_by_role("button", name="New incident").focus()
    assert page.evaluate(
        "document.activeElement === document.querySelector('#new-incident')"
    )
