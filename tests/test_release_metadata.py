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


def test_favicon_request_does_not_create_browser_error_noise() -> None:
    response = TestClient(app).get("/favicon.ico")

    assert response.status_code == 204
    assert response.content == b""


def test_release_documents_record_completed_interactive_gate() -> None:
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    checklist = Path("docs/release-checklist-v0.1.0.md").read_text(encoding="utf-8")
    release_notes = Path("docs/release-notes-v0.1.0.md").read_text(encoding="utf-8")
    validator = Path("tools/validate-release-windows.ps1").read_text(encoding="utf-8")

    assert "## [0.1.0] - 2026-07-14" in changelog
    assert "Interactive Windows validation passed" in changelog
    assert "- [x] The generated `release-validation.md` result was **PASS**." in checklist
    assert "- [x] The evidence archive was reviewed and summarized in issue #18." in checklist
    assert "- [ ] Create annotated tag `v0.1.0`" in checklist
    assert "INFIOS v0.1.0" in release_notes
    assert "INFIOS_RELEASE_VALIDATION_" in validator
    assert "Compress-Archive" in validator
    assert "Upload-ready ZIP" in validator
    assert "Upload the ZIP archive to GitHub issue #18" in validator
    assert "- Python launcher: `$launcher`" not in validator
    assert "- Health version: `$($health.version)`" not in validator
