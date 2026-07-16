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
def catalogue_base_url() -> str:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
            raise RuntimeError("Catalogue UI server did not become healthy.")
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def test_catalogue_list_detail_and_completeness(page: Page, catalogue_base_url: str) -> None:
    service = {"service_id":"service-app","name":"Order Management","kind":"application","description":"Order workflow service.","owner_team":"Application Support","support_contact":"support@example.invalid","criticality":"high","environments":["production"],"runbook_reference":"RB-100","status_page_reference":None,"active":True,"created_at":"2026-07-16T10:00:00Z","updated_at":"2026-07-16T10:00:00Z"}
    dependency = {"dependency_id":"dependency-1","source_service_id":"service-app","target_service_id":"service-db","dependency_type":"data","required":True,"description":"Reads order records.","created_at":"2026-07-16T10:00:00Z"}
    completeness = {"status":"attention_required","service_count":1,"active_service_count":1,"dependency_count":1,"services_requiring_attention":1,"issue_counts":{"status_page_reference":1},"services":[{"service_id":"service-app","name":"Order Management","active":True,"status":"attention_required","missing_information":["status_page_reference"],"dependency_count":1}],"interpretation_note":"Context only."}

    def api(route: Route) -> None:
        url = route.request.url
        if url.endswith("/api/catalogue/services?active_only=false"):
            route.fulfill(json={"services":[service],"count":1})
        elif url.endswith("/api/catalogue/completeness-report?include_inactive=true"):
            route.fulfill(json=completeness)
        elif url.endswith("/api/catalogue/services/service-app/dependencies"):
            route.fulfill(json={"dependencies":[dependency],"count":1})
        elif url.endswith("/api/catalogue/services/service-app"):
            route.fulfill(json=service)
        else:
            route.continue_()

    page.route("**/api/catalogue/**", api)
    page.goto(f"{catalogue_base_url}/catalogue")
    expect(page.get_by_role("heading", name="Order Management")).to_be_visible()
    expect(page.get_by_text("Application Support", exact=True)).to_be_visible()
    expect(page.get_by_text("service-app → service-db")).to_be_visible()
    expect(page.get_by_text("Missing operational context: status page reference.")).to_be_visible()
    expect(page.get_by_text("They do not prove service failure", exact=False)).to_be_visible()
    Path("browser-artifacts").mkdir(exist_ok=True)
    page.screenshot(path="browser-artifacts/catalogue-ui.png", full_page=True)
