from __future__ import annotations

import socket
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest
from playwright.sync_api import Page


SURFACES = (
    ("/problems", ".problem-panel"),
    ("/handovers", ".handover-panel"),
    ("/catalogue", ".catalogue-panel"),
    ("/analytics", ".analytics-panel"),
)


@pytest.fixture(scope="module")
def density_base_url() -> str:
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
            raise RuntimeError("Density test server did not become healthy.")
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.mark.parametrize(("surface", "panel_selector"), SURFACES)
def test_secondary_surfaces_use_compact_components(
    page: Page,
    density_base_url: str,
    surface: str,
    panel_selector: str,
) -> None:
    page.set_viewport_size({"width": 1440, "height": 1000})
    response = page.goto(f"{density_base_url}{surface}")
    assert response is not None and response.status == 200

    values = page.evaluate(
        """(panelSelector) => {
          const panel = document.querySelector(panelSelector);
          const intro = document.querySelector('#main-content > :first-child');
          const panelStyle = getComputedStyle(panel);
          const introStyle = getComputedStyle(intro);
          return {
            panelPadding: parseFloat(panelStyle.paddingTop),
            panelRadius: parseFloat(panelStyle.borderTopLeftRadius),
            panelShadow: panelStyle.boxShadow,
            introRadius: parseFloat(introStyle.borderTopLeftRadius),
            introShadow: introStyle.boxShadow,
          };
        }""",
        panel_selector,
    )
    assert values["panelPadding"] <= 20
    assert values["panelRadius"] <= 12
    assert values["introRadius"] == 0
    assert values["introShadow"] == "none"

    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 1


def test_analytics_metrics_use_compact_dashboard_scale(page: Page, density_base_url: str) -> None:
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(f"{density_base_url}/analytics")
    values = page.evaluate(
        """() => {
          const card = document.querySelector('.metric-card');
          const value = card.querySelector('strong');
          const label = card.querySelector('span');
          return {
            padding: parseFloat(getComputedStyle(card).paddingTop),
            radius: parseFloat(getComputedStyle(card).borderTopLeftRadius),
            valueSize: parseFloat(getComputedStyle(value).fontSize),
            labelTransform: getComputedStyle(label).textTransform,
          };
        }"""
    )
    assert values["padding"] <= 16
    assert values["radius"] <= 10
    assert values["valueSize"] <= 32
    assert values["labelTransform"] == "uppercase"
