from pathlib import Path
import tomllib

from fastapi.testclient import TestClient

from app.main import app
from app.version import VERSION


def test_runtime_package_and_api_versions_match() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert VERSION == "0.1.0"
    assert pyproject["project"]["version"] == VERSION
    assert app.version == VERSION


def test_health_endpoint_exposes_release_identity() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "infios-app-support-workbench",
        "version": VERSION,
    }


def test_release_documents_track_pending_windows_gate() -> None:
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    checklist = Path("docs/release-checklist-v0.1.0.md").read_text(encoding="utf-8")

    assert "## [0.1.0] - Unreleased" in changelog
    assert "Windows bootstrap smoke test" in changelog
    assert "- [ ] `.venv` is created when absent." in checklist
    assert "- [ ] Create annotated tag `v0.1.0`" in checklist
