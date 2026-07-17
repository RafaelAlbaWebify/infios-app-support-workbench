from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_UI_FILES = {
    "analytics.html",
    "catalogue.html",
    "handovers.html",
    "index.html",
    "problems.html",
    "styles.css",
}


def test_wheel_contains_runtime_assets_and_imports_outside_checkout(tmp_path) -> None:
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    wheels = list(dist.glob("*.whl"))
    assert len(wheels) == 1

    with zipfile.ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())
    packaged_ui = {
        Path(name).name
        for name in names
        if name.startswith("app/ui/") and not name.endswith("/")
    }
    assert REQUIRED_UI_FILES <= packaged_ui
    assert any(name.endswith(".dist-info/entry_points.txt") for name in names)

    target = tmp_path / "installed"
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(target), str(wheels[0])],
        check=True,
        capture_output=True,
        text=True,
    )

    probe = """
from app.api.ui import UI_DIR
from app.main import app
from app.version import VERSION
required = {'index.html', 'analytics.html', 'problems.html', 'handovers.html', 'catalogue.html', 'styles.css'}
assert required <= {path.name for path in UI_DIR.iterdir() if path.is_file()}
paths = {route.path for route in app.routes}
assert {'/', '/analytics', '/problems', '/handovers', '/catalogue', '/api/health'} <= paths
assert VERSION == '0.1.0'
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(target)
    subprocess.run(
        [sys.executable, "-I", "-c", probe],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
