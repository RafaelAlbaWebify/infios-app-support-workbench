from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_distribution_builder_creates_self_contained_package_contract(tmp_path) -> None:
    result = subprocess.run(
        [sys.executable, "tools/build_windows_package.py", "--output", str(tmp_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    archive = Path(result.stdout.strip().splitlines()[-1])
    assert archive.exists()
    assert archive.name == "INFIOS-0.1.0-windows.zip"

    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())
        root = "INFIOS-0.1.0-windows/"
        assert f"{root}Start-INFIOS.ps1" in names
        assert f"{root}README.txt" in names
        assert f"{root}data/README.txt" in names
        wheels = [name for name in names if name.startswith(f"{root}wheels/") and name.endswith(".whl")]
        assert len(wheels) == 1

        launcher = package.read(f"{root}Start-INFIOS.ps1").decode("utf-8")
        readme = package.read(f"{root}README.txt").decode("utf-8")

    assert "python -m venv" in launcher
    assert "app.cli" in launcher
    assert "infios-cases.sqlite3" in launcher
    assert "Python 3.10 or newer" in readme
    assert "Start-INFIOS.ps1" in readme
