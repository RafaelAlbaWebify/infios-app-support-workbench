from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "http://127.0.0.1:8768"


@pytest.fixture(scope="module", autouse=True)
def accessibility_server() -> None:
    Path("browser-artifacts").mkdir(exist_ok=True)
    env = os.environ.copy()
    env["INFIOS_DB_PATH"] = str(Path("browser-artifacts/accessibility-tests.sqlite3").resolve())
    process = subprocess.Popen(
        ["python", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8768"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{BASE_URL}/api/health", timeout=0.5).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.2)
    else:
        process.terminate()
        raise RuntimeError("INFIOS accessibility server did not become ready")

    yield

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def _structural_violations(page: Page) -> dict[str, list[str]]:
    return page.evaluate(
        """
        () => {
          const visible = (element) => {
            if (element.closest('details:not([open])') && element.tagName !== 'SUMMARY') return false;
            const style = getComputedStyle(element);
            return style.display !== 'none' && style.visibility !== 'hidden' && element.getClientRects().length > 0;
          };
          const ids = [...document.querySelectorAll('[id]')].map((element) => element.id);
          const duplicateIds = [...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))];
          const unlabeledControls = [...document.querySelectorAll('input, select, textarea')]
            .filter(visible)
            .filter((element) => element.type !== 'hidden')
            .filter((element) => !element.labels?.length && !element.getAttribute('aria-label') && !element.getAttribute('aria-labelledby'))
            .map((element) => element.id || element.outerHTML.slice(0, 100));
          const unnamedInteractive = [...document.querySelectorAll('button, a[href], summary')]
            .filter(visible)
            .filter((element) => !(element.textContent || element.getAttribute('aria-label') || element.getAttribute('aria-labelledby') || '').trim())
            .map((element) => element.id || element.outerHTML.slice(0, 100));
          return { duplicateIds, unlabeledControls, unnamedInteractive };
        }
        """
    )


def test_dashboard_has_skip_link_live_status_and_clean_structure(page: Page) -> None:
    page.goto(BASE_URL)
    expect(page.locator("h1")).to_have_count(1)
    expect(page.get_by_role("status")).to_have_attribute("aria-live", "polite")

    page.keyboard.press("Tab")
    skip_link = page.get_by_role("link", name="Skip to main content")
    expect(skip_link).to_be_focused()
    expect(skip_link).to_be_visible()
    page.keyboard.press("Enter")
    expect(page.locator("#main-content")).to_be_focused()

    violations = _structural_violations(page)
    assert violations == {
        "duplicateIds": [],
        "unlabeledControls": [],
        "unnamedInteractive": [],
    }


def test_active_case_controls_are_labeled_and_focus_is_visible(page: Page) -> None:
    page.goto(BASE_URL)
    page.get_by_role("button", name="New incident").click()
    page.get_by_label("Application or service").fill("Order Management")
    page.get_by_label("Short problem description").fill("Accessibility audit case")
    page.get_by_role("button", name="Create incident and continue").click()

    violations = _structural_violations(page)
    assert violations == {
        "duplicateIds": [],
        "unlabeledControls": [],
        "unnamedInteractive": [],
    }

    evidence_button = page.get_by_role("button", name="HTTP/API evidence")
    for _ in range(40):
        page.keyboard.press("Tab")
        if evidence_button.evaluate("element => document.activeElement === element"):
            break
    expect(evidence_button).to_be_focused()
    focus_style = evidence_button.evaluate(
        "element => ({ outline: getComputedStyle(element).outlineStyle, width: getComputedStyle(element).outlineWidth })"
    )
    assert focus_style["outline"] != "none"
    assert focus_style["width"] != "0px"
