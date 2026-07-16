from fastapi.testclient import TestClient

from app.api.known_errors import get_known_error_repository
from app.api.problems import get_problem_repository
from app.known_error_models import KnownErrorRecord
from app.main import app
from app.problem_models import ProblemRecord


class ProblemRepo:
    def __init__(self):
        self.problem = ProblemRecord(problem_id="problem-1", title="Repeated issue", summary="Grouped cases", owner="L2", created_by="L2", case_ids=["case-1"])

    def get(self, problem_id):
        return self.problem if problem_id == self.problem.problem_id else None


class KnownErrorRepo:
    def __init__(self):
        self.items = {}

    def save(self, record):
        self.items[record.known_error_id] = record
        return record

    def get(self, known_error_id):
        return self.items.get(known_error_id)

    def list_for_problem(self, problem_id, limit=200):
        return [item for item in self.items.values() if item.problem_id == problem_id][:limit]


def payload():
    return {
        "title": "Temporary workaround",
        "symptom_summary": "Stored symptom pattern",
        "workaround_steps": ["Compare the symptom with the record", "Use the referenced support procedure"],
        "workaround_limitations": "Temporary guidance only; recurrence remains possible.",
        "validation_guidance": "Confirm the affected operation completes and attach case evidence.",
        "safety": "approved_change_required",
        "owner": "Application Support",
        "created_by": "Rafael",
    }


def test_create_publish_list_and_retire_known_error():
    problem_repository = ProblemRepo()
    repository = KnownErrorRepo()
    app.dependency_overrides[get_problem_repository] = lambda: problem_repository
    app.dependency_overrides[get_known_error_repository] = lambda: repository
    client = TestClient(app)
    try:
        created = client.post("/api/problems/problem-1/known-errors", json=payload())
        assert created.status_code == 201
        known_error_id = created.json()["known_error_id"]
        assert created.json()["status"] == "draft"

        published = client.post(
            f"/api/problems/problem-1/known-errors/{known_error_id}/publish",
            json={"approved_by": "Service Owner", "approval_reason": "Reviewed against the support procedure"},
        )
        assert published.status_code == 200
        assert published.json()["status"] == "published"
        assert published.json()["approved_at"] is not None

        listed = client.get("/api/problems/problem-1/known-errors")
        assert listed.status_code == 200
        assert listed.json()["count"] == 1

        retired = client.post(f"/api/problems/problem-1/known-errors/{known_error_id}/retire")
        assert retired.status_code == 200
        assert retired.json()["status"] == "retired"
    finally:
        app.dependency_overrides.clear()


def test_model_rejects_incomplete_publication_metadata():
    data = payload()
    data["status"] = "published"
    try:
        KnownErrorRecord(problem_id="problem-1", **data)
    except ValueError as exc:
        assert "approving operator" in str(exc)
    else:
        raise AssertionError("Publication metadata should be required")
