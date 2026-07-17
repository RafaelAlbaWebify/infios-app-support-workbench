from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import pytest
from playwright.sync_api import Page, Route, expect


@pytest.fixture(scope="module")
def problems_base_url() -> str:
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
            raise RuntimeError("Problem UI server did not become healthy.")
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def test_problem_detail_audit_and_browser_filters(page: Page, problems_base_url: str) -> None:
    status_submitted = []
    publish_submitted = []
    problem = {
        "problem_id": "problem-1", "title": "Repeated order issue", "summary": "Two linked cases.",
        "status": "open", "owner": "L2 Support", "created_by": "L2 Support",
        "case_ids": ["case-1", "case-2"], "status_history": [],
        "created_at": "2026-07-16T07:00:00Z", "updated_at": "2026-07-16T07:00:00Z",
        "occurrence_count": 2,
    }
    actions = [
        {"title": "Review action plan", "status": "planned", "action_type": "corrective", "owner": "Engineering", "due_date": "2026-07-20"},
        {"title": "Monitor order queue", "status": "implemented", "action_type": "monitoring", "owner": "L2 Support", "due_date": None},
    ]
    draft_guidance = {
        "known_error_id": "known-1", "problem_id": "problem-1", "title": "Temporary order recovery guidance",
        "symptom_summary": "Order processing remains pending.", "workaround_steps": ["Verify case scope", "Follow approved runbook"],
        "workaround_limitations": "Use only for the documented symptom.", "validation_guidance": "Confirm the affected order resumes.",
        "safety": "approved_change_required", "requires_write_or_restart": True, "owner": "L2 Support", "created_by": "L2 Support",
        "status": "draft", "approved_by": None, "approval_reason": None, "approved_at": None,
        "created_at": "2026-07-16T07:00:00Z", "updated_at": "2026-07-16T07:00:00Z",
    }
    published_guidance = {
        "known_error_id": "known-2", "problem_id": "problem-1", "title": "Read-only queue verification",
        "symptom_summary": "Queue state needs confirmation.", "workaround_steps": ["Inspect queue state"],
        "workaround_limitations": "Observation only.", "validation_guidance": "Record the observed queue state.",
        "safety": "read_only", "requires_write_or_restart": False, "owner": "Operations", "created_by": "Operations",
        "status": "published", "approved_by": "L2 Lead", "approval_reason": "Read-only verification reviewed", "approved_at": "2026-07-16T08:00:00Z",
        "created_at": "2026-07-16T07:30:00Z", "updated_at": "2026-07-16T08:00:00Z",
    }

    def api(route: Route) -> None:
        url = route.request.url
        if url.endswith("/api/problems?active_only=false"):
            route.fulfill(json={"problems": [problem], "count": 1})
        elif url.endswith("/api/problems/problem-1/rca"):
            route.fulfill(json={"statements": [{"statement": "Cause statement under review", "status": "draft", "supporting_explanation_ids": []}], "count": 1})
        elif url.endswith("/api/problems/problem-1/actions"):
            route.fulfill(json={"actions": actions, "count": len(actions)})
        elif url.endswith("/api/problems/problem-1/known-errors/known-1/publish") and route.request.method == "POST":
            publish_submitted.append(json.loads(route.request.post_data or "{}"))
            draft_guidance.update({"status": "published", "approved_by": "Rafael", "approval_reason": "Reviewed for operational use"})
            route.fulfill(json=draft_guidance)
        elif url.endswith("/api/problems/problem-1/known-errors"):
            route.fulfill(json={"records": [draft_guidance, published_guidance], "count": 2})
        elif url.endswith("/api/problems/problem-1/closure-readiness"):
            route.fulfill(json={"ready_for_operator_review": False, "blockers": ["no_confirmed_rca", "actions_not_validated"]})
        elif url.endswith("/api/problems/problem-1/status") and route.request.method == "POST":
            status_submitted.append(json.loads(route.request.post_data or "{}"))
            problem["status"] = "investigating"
            problem["status_history"] = [{"from_status": "open", "to_status": "investigating", "changed_by": "Rafael", "reason": "Accepted for investigation", "changed_at": "2026-07-16T07:30:00Z"}]
            route.fulfill(json=problem)
        elif url.endswith("/api/problems/problem-1"):
            route.fulfill(json=problem)
        else:
            route.continue_()

    page.route("**/api/problems**", api)
    page.goto(f"{problems_base_url}/problems")
    expect(page.get_by_role("heading", name="Repeated order issue")).to_be_visible()
    expect(page.locator("#action-count")).to_have_text("2 actions")

    page.locator("#action-search").fill("queue")
    expect(page.locator("#action-count")).to_have_text("1 of 2 actions")
    expect(page.get_by_text("Monitor order queue")).to_be_visible()
    expect(page.get_by_text("Review action plan")).to_be_hidden()

    page.locator("#action-search").fill("")
    page.locator("#action-status-filter").select_option("planned")
    expect(page.locator("#action-count")).to_have_text("1 of 2 actions")
    expect(page.get_by_text("Review action plan")).to_be_visible()

    page.locator("#action-status-filter").select_option("")
    page.locator("#action-type-filter").select_option("monitoring")
    page.locator("#action-owner-filter").fill("L2")
    expect(page.locator("#action-count")).to_have_text("1 of 2 actions")
    expect(page.get_by_text("Monitor order queue")).to_be_visible()

    page.locator("#action-owner-filter").fill("missing")
    expect(page.locator("#action-filter-empty")).to_be_visible()
    page.locator("#clear-action-filters").click()
    expect(page.locator("#action-count")).to_have_text("2 actions")

    expect(page.locator("#known-error-count")).to_have_text("2 records")
    page.locator("#known-error-search").fill("queue verification")
    expect(page.locator("#known-error-count")).to_have_text("1 of 2 records")
    expect(page.get_by_text("Read-only queue verification")).to_be_visible()
    expect(page.get_by_text("Temporary order recovery guidance")).to_be_hidden()

    page.locator("#known-error-search").fill("")
    page.locator("#known-error-status-filter").select_option("draft")
    expect(page.locator("#known-error-count")).to_have_text("1 of 2 records")
    expect(page.get_by_text("Temporary order recovery guidance")).to_be_visible()

    page.locator("#known-error-status-filter").select_option("")
    page.locator("#known-error-safety-filter").select_option("read only")
    page.locator("#known-error-owner-filter").fill("Operations")
    expect(page.locator("#known-error-count")).to_have_text("1 of 2 records")
    expect(page.get_by_text("Read-only queue verification")).to_be_visible()

    page.locator("#known-error-owner-filter").fill("missing")
    expect(page.locator("#known-error-filter-empty")).to_be_visible()
    page.locator("#clear-known-error-filters").click()
    expect(page.locator("#known-error-count")).to_have_text("2 records")

    expect(page.locator("#problem-known-errors").get_by_text("approved change required", exact=False)).to_be_visible()
    page.get_by_role("button", name="Review and publish").click()
    page.locator("#known-error-approved-by").fill("Rafael")
    page.locator("#known-error-approval-reason").fill("Reviewed for operational use")
    page.get_by_role("button", name="Apply known-error action").click()
    expect(page.locator("#problem-status-message")).to_contain_text("published with approval audit")
    expect(page.get_by_role("button", name="Retire guidance")).to_have_count(2)
    page.locator("#new-problem-status").select_option("investigating")
    page.locator("#problem-changed-by").fill("Rafael")
    page.locator("#problem-change-reason").fill("Accepted for investigation")
    page.get_by_role("button", name="Save status change").click()
    expect(page.get_by_text("open → investigating")).to_be_visible()
    assert publish_submitted == [{"approved_by": "Rafael", "approval_reason": "Reviewed for operational use"}]
    assert status_submitted == [{"to_status": "investigating", "changed_by": "Rafael", "reason": "Accepted for investigation"}]
    Path("browser-artifacts").mkdir(exist_ok=True)
    page.screenshot(path="browser-artifacts/problem-management-ui.png", full_page=True)
