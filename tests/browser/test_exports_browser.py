from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "http://127.0.0.1:8766"


@pytest.fixture(scope="module", autouse=True)
def export_server() -> None:
    Path("browser-artifacts").mkdir(exist_ok=True)
    env = os.environ.copy()
    env["INFIOS_DB_PATH"] = str(Path("browser-artifacts/export-tests.sqlite3").resolve())
    process = subprocess.Popen(
        [
            "python",
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8766",
        ],
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
        raise RuntimeError("INFIOS export server did not become ready")

    yield

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def test_case_summary_and_escalation_downloads_are_available(page: Page, tmp_path) -> None:
    case_response = page.request.post(
        f"{BASE_URL}/api/cases",
        data={
            "title": "Export workflow check",
            "application": "Order Management",
            "impact": "Important function unavailable",
            "affected_scope": "Several users",
        },
    )
    assert case_response.ok
    support_case = case_response.json()
    case_id = support_case["case_id"]

    package_response = page.request.post(
        f"{BASE_URL}/api/cases/{case_id}/escalations",
        data={
            "target_team": "L2 Application Support",
            "requested_action": "Review the application logs and correlate the captured timestamp with the complete request path, correlation identifier, deployment history, dependency health, and any matching backend exception without assuming that temporal proximity proves causation.",
        },
    )
    assert package_response.ok
    package = package_response.json()

    page.goto(BASE_URL)
    page.get_by_role("button", name=f"Open incident {support_case['title']}").click()

    summary_link = page.get_by_role("link", name="Download case summary")
    expect(summary_link).to_have_attribute("href", f"/api/cases/{case_id}/summary/download")
    with page.expect_download() as summary_download_info:
        summary_link.click()
    summary_download = summary_download_info.value
    assert summary_download.suggested_filename == f"infios-{case_id}-summary.md"
    assert "# Case summary: Export workflow check" in Path(summary_download.path()).read_text(encoding="utf-8")

    page.get_by_role("navigation", name="Case work areas").get_by_role(
        "link", name="Escalation"
    ).click()
    handover_link = page.get_by_role("link", name="Download Markdown")
    expect(handover_link).to_have_attribute(
        "href",
        f"/api/cases/{case_id}/escalations/{package['package_id']}/download",
    )

    preview_fits = page.locator("#escalation-preview").evaluate(
        "element => element.scrollWidth <= element.clientWidth"
    )
    assert preview_fits is True
    report_fits = page.locator("#escalation-preview pre").evaluate(
        "element => element.scrollWidth <= element.clientWidth"
    )
    assert report_fits is True
    assert page.locator("#escalation-preview pre").evaluate(
        "element => getComputedStyle(element).whiteSpace"
    ) == "pre-wrap"

    with page.expect_download() as handover_download_info:
        handover_link.click()
    handover_download = handover_download_info.value
    assert package["package_id"] in handover_download.suggested_filename
    assert "# Escalation: Export workflow check" in Path(handover_download.path()).read_text(encoding="utf-8")
