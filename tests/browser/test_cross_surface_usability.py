from __future__ import annotations

import socket
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest
from playwright.sync_api import Page, expect


SURFACES = ("/", "/problems", "/handovers", "/catalogue", "/analytics")


@pytest.fixture(scope="module")
def usability_base_url() -> str:
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
            raise RuntimeError("Usability test server did not become healthy.")
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.mark.parametrize("surface", SURFACES)
def test_operator_surfaces_remain_keyboard_accessible_without_mobile_overflow(
    page: Page,
    usability_base_url: str,
    surface: str,
) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page_errors: list[str] = []
    console_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)

    response = page.goto(f"{usability_base_url}{surface}")
    assert response is not None and response.status == 200
    expect(page.locator("#main-content")).to_be_visible()
    expect(page.get_by_role("navigation", name="Primary")).to_be_visible()

    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 1

    page.locator("body").press("Home")
    page.keyboard.press("Tab")
    expect(page.locator(".skip-link")).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator("#main-content")).to_be_focused()

    assert page_errors == []
    assert console_errors == []


def test_incident_surface_uses_shared_product_shell(page: Page, usability_base_url: str) -> None:
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(f"{usability_base_url}/")

    shell = page.locator(".infios-app-shell")
    sidebar = page.locator(".infios-product-sidebar")
    navigation = page.get_by_role("navigation", name="Primary")
    expect(shell).to_be_visible()
    expect(sidebar).to_be_visible()
    expect(navigation.get_by_role("link")).to_have_count(5)
    expect(page.locator("#open-incidents")).to_have_attribute("aria-current", "page")
    expect(page.locator("#open-problems")).to_have_attribute("href", "/problems")
    expect(page.locator("#open-handovers")).to_have_attribute("href", "/handovers")
    expect(page.locator("#open-catalogue")).to_have_attribute("href", "/catalogue")
    expect(page.locator("#open-analytics")).to_have_attribute("href", "/analytics")

    geometry = page.evaluate(
        """() => {
          const sidebar = document.querySelector('.infios-product-sidebar').getBoundingClientRect();
          const content = document.querySelector('.infios-app-content').getBoundingClientRect();
          return { sidebarWidth: sidebar.width, sidebarHeight: sidebar.height, contentLeft: content.left };
        }"""
    )
    assert 220 <= geometry["sidebarWidth"] <= 280
    assert geometry["sidebarHeight"] >= 900
    assert geometry["contentLeft"] >= geometry["sidebarWidth"] - 1

    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 1
