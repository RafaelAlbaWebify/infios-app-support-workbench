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


def _create_case(page: Page, title: str = "Orders page fails after login") -> None:
    page.goto(BASE_URL)
    page.get_by_role("button", name="New incident").click()
    page.get_by_label("Application or service").fill("Order Management")
    page.get_by_label("Short problem description").fill(title)
    page.get_by_role("button", name="Create incident and continue").click()


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
    expect(page.get_by_role("navigation", name="Case work areas")).to_be_visible()
    expect(page.locator("#action-result-editor")).to_be_hidden()
    expect(page.locator("#work-explanations")).not_to_have_attribute("open", "")
    expect(page.locator("#work-escalation")).not_to_have_attribute("open", "")
    expect(page.locator("#work-recovery")).not_to_have_attribute("open", "")
    _capture(page, "desktop-new-case-compact.png")


def test_case_work_navigation_opens_and_focuses_advanced_area(page: Page) -> None:
    _create_case(page, "Navigation quality check")
    navigation = page.get_by_role("navigation", name="Case work areas")
    expect(navigation).to_be_visible()

    navigation.get_by_role("link", name="L2 explanations").click()
    expect(page.locator("#work-explanations")).to_have_attribute("open", "")
    expect(page.locator("#work-explanations > summary")).to_be_focused()

    navigation.get_by_role("link", name="Lifecycle & recovery").click()
    expect(page.locator("#work-recovery")).to_have_attribute("open", "")
    expect(page.locator("#work-recovery > summary")).to_be_focused()
    _capture(page, "desktop-navigation-open.png")


def test_evidence_observation_and_timeline_workflow(page: Page) -> None:
    _create_case(page, "Orders API returns 500")

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


def test_full_l1_to_l2_recovery_and_export_workflow(page: Page) -> None:
    _create_case(page, "Full lifecycle browser proof")

    page.get_by_role("button", name="HTTP/API evidence").click()
    page.get_by_label("Source", exact=True).fill("Browser developer tools")
    page.get_by_label("What did you observe?").fill("POST /api/orders returned HTTP 500 at 10:14")
    page.get_by_label("How certain is this information?").select_option("technically_confirmed")
    page.get_by_role("button", name="Save evidence").click()
    expect(page.get_by_text("POST /api/orders returned HTTP 500 at 10:14")).to_be_visible()

    page.get_by_label("Factual statement").fill("HTTP 500 was observed after successful login.")
    page.locator("#observation-evidence").select_option(index=0)
    page.get_by_role("button", name="Save observation").click()
    expect(page.locator("#observation-list").get_by_text("HTTP 500 was observed after successful login.", exact=True)).to_be_visible()

    page.get_by_role("button", name="Review case guidance").click()
    first_check = page.locator("#guided-check-list .check-card").first
    expect(first_check).to_be_visible()
    first_check.get_by_role("button", name="Start this safe check").click()
    page.get_by_label("What happened?").fill("The same HTTP 500 reproduced with a second approved test user.")
    page.get_by_label("Conclusion, if supported").fill("The issue is less likely to be isolated to one user.")
    page.get_by_label("Performed by").fill("L1 Support")
    page.get_by_role("button", name="Save check result").click()
    expect(page.locator("#action-list").get_by_text("Result: The same HTTP 500 reproduced with a second approved test user.", exact=True)).to_be_visible()

    navigation = page.get_by_role("navigation", name="Case work areas")
    navigation.get_by_role("link", name="Escalation").click()
    page.get_by_label("What should the receiving team do?").fill("Review application logs for the captured endpoint and timestamp.")
    page.get_by_role("button", name="Generate L2 handover").click()
    expect(page.get_by_role("heading", name="Handover for L2 Application Support")).to_be_visible()
    expect(page.get_by_role("link", name="Download Markdown")).to_be_visible()

    navigation.get_by_role("link", name="Lifecycle & recovery").click()
    page.get_by_label("Next status").select_option("information_gathering")
    page.get_by_role("button", name="Change status").click()
    expect(page.locator("#lifecycle-status")).to_have_text("information gathering")
    page.get_by_label("Next status").select_option("investigation")
    page.get_by_role("button", name="Change status").click()
    expect(page.locator("#lifecycle-status")).to_have_text("investigation")
    page.get_by_label("Next status").select_option("recovery_validation")
    page.get_by_role("button", name="Change status").click()
    expect(page.locator("#lifecycle-status")).to_have_text("recovery validation")

    page.get_by_label("Outcome").select_option("passed")
    page.get_by_label("Method").fill("Repeat order submission after service recovery")
    page.get_by_label("Result").fill("Order submission completed successfully and no HTTP 500 was observed.")
    page.get_by_label("Performed by").last.fill("L1 Support and affected user")
    page.locator("#recovery-evidence").select_option(index=0)
    page.get_by_role("button", name="Save recovery validation").click()
    expect(page.locator("#recovery-list").get_by_text("Order submission completed successfully and no HTTP 500 was observed.", exact=True)).to_be_visible()

    page.get_by_label("Next status").select_option("resolved")
    page.get_by_role("button", name="Change status").click()
    expect(page.locator("#lifecycle-status")).to_have_text("resolved")

    summary_link = page.get_by_role("link", name="Download case summary")
    expect(summary_link).to_be_visible()
    with page.expect_download() as download_info:
        summary_link.click()
    downloaded = download_info.value
    summary_text = Path(downloaded.path()).read_text(encoding="utf-8")
    assert "# Case summary: Full lifecycle browser proof" in summary_text
    assert "HTTP 500 was observed after successful login." in summary_text
    assert "Order submission completed successfully" in summary_text

    _capture(page, "desktop-full-lifecycle-resolved.png")


def test_mobile_layout_has_no_horizontal_overflow(page: Page) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    _create_case(page, "Mobile navigation check")
    expect(page.get_by_role("navigation", name="Case work areas")).to_be_visible()

    overflow = page.evaluate(
        "document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert overflow is False
    page.get_by_role("navigation", name="Case work areas").get_by_role(
        "link", name="Escalation"
    ).click()
    expect(page.locator("#work-escalation")).to_have_attribute("open", "")
    overflow_after_open = page.evaluate(
        "document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert overflow_after_open is False
    _capture(page, "mobile-case-navigation.png")


def test_basic_accessibility_contract(page: Page) -> None:
    page.goto(BASE_URL)
    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page.get_by_role("main")).to_be_visible()
    expect(page.locator("button:not([type])")).to_have_count(0)

    page.get_by_role("button", name="New incident").focus()
    assert page.evaluate(
        "document.activeElement === document.querySelector('#new-incident')"
    )
