from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
_version_namespace: dict[str, object] = {}
exec((ROOT / "app" / "version.py").read_text(encoding="utf-8"), _version_namespace)
VERSION = str(_version_namespace["VERSION"])
PACKAGE_NAME = f"INFIOS-{VERSION}-windows"


def build_package(output_directory: Path) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="infios-package-") as temporary:
        temporary_path = Path(temporary)
        wheel_directory = temporary_path / "wheel"
        staging_root = temporary_path / PACKAGE_NAME
        package_wheels = staging_root / "wheels"
        package_data = staging_root / "data"

        subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(wheel_directory)],
            cwd=ROOT,
            check=True,
        )
        wheels = list(wheel_directory.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"Expected one wheel, found {len(wheels)}.")

        package_wheels.mkdir(parents=True)
        package_data.mkdir(parents=True)
        shutil.copy2(wheels[0], package_wheels / wheels[0].name)
        shutil.copy2(ROOT / "tools" / "start-infios-package.ps1", staging_root / "Start-INFIOS.ps1")
        (package_data / "README.txt").write_text(
            "INFIOS stores its local SQLite database in this directory by default.\n",
            encoding="utf-8",
        )
        (staging_root / "README.txt").write_text(
            "INFIOS Application Support Workbench\n"
            f"Version: {VERSION}\n\n"
            "Requirements:\n"
            "- Windows 10 or newer\n"
            "- Python 3.10 or newer available as the 'python' command\n"
            "- Internet access during first launch to install Python dependencies\n\n"
            "Start:\n"
            "1. Extract the ZIP to a writable folder.\n"
            "2. Right-click Start-INFIOS.ps1 and run with PowerShell, or execute:\n"
            "   powershell -ExecutionPolicy Bypass -File .\\Start-INFIOS.ps1\n\n"
            "The package creates a private .runtime environment and stores data under .\\data.\n",
            encoding="utf-8",
        )

        archive_path = output_directory / f"{PACKAGE_NAME}.zip"
        if archive_path.exists():
            archive_path.unlink()
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(staging_root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(temporary_path))
        return archive_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the INFIOS Windows distribution ZIP.")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    archive = build_package(args.output.resolve())
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
