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


def test_problem_detail_and_audited_status_change(page: Page, problems_base_url: str) -> None:
    submitted = []
    problem = {
        "problem_id": "problem-1", "title": "Repeated order issue", "summary": "Two linked cases.",
        "status": "open", "owner": "L2 Support", "created_by": "L2 Support",
        "case_ids": ["case-1", "case-2"], "status_history": [],
        "created_at": "2026-07-16T07:00:00Z", "updated_at": "2026-07-16T07:00:00Z",
        "occurrence_count": 2,
    }

    def api(route: Route) -> None:
        url = route.request.url
        if url.endswith("/api/problems?active_only=false"):
            route.fulfill(json={"problems": [problem], "count": 1})
        elif url.endswith("/api/problems/problem-1/rca"):
            route.fulfill(json={"statements": [{"statement": "Cause statement under review", "status": "draft", "supporting_explanation_ids": []}], "count": 1})
        elif url.endswith("/api/problems/problem-1/actions"):
            route.fulfill(json={"actions": [{"title": "Review action plan", "status": "planned", "action_type": "corrective", "owner": "Engineering"}], "count": 1})
        elif url.endswith("/api/problems/problem-1/closure-readiness"):
            route.fulfill(json={"ready_for_operator_review": False, "blockers": ["no_confirmed_rca", "actions_not_validated"]})
        elif url.endswith("/api/problems/problem-1/status") and route.request.method == "POST":
            submitted.append(json.loads(route.request.post_data or "{}"))
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
    expect(page.get_by_text("no confirmed rca")).to_be_visible()
    page.locator("#new-problem-status").select_option("investigating")
    page.locator("#problem-changed-by").fill("Rafael")
    page.locator("#problem-change-reason").fill("Accepted for investigation")
    page.get_by_role("button", name="Save status change").click()
    expect(page.locator("#problem-status-message")).to_contain_text("Status change saved")
    expect(page.get_by_text("open → investigating")).to_be_visible()
    assert submitted == [{"to_status": "investigating", "changed_by": "Rafael", "reason": "Accepted for investigation"}]
    Path("browser-artifacts").mkdir(exist_ok=True)
    page.screenshot(path="browser-artifacts/problem-management-ui.png", full_page=True)
