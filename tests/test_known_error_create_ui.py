from fastapi.testclient import TestClient

from app.main import app


def test_problem_page_exposes_known_error_draft_form():
    response = TestClient(app).get('/problems')
    assert response.status_code == 200
    assert 'Create known-error draft' in response.text
    assert 'Limitations' in response.text
    assert 'Validation guidance' in response.text
    assert '/ui/static/known-error-create.js' in response.text


def test_known_error_create_script_sends_required_draft_fields():
    response = TestClient(app).get('/ui/static/known-error-create.js')
    assert response.status_code == 200
    for field in (
        'symptom_summary',
        'workaround_steps',
        'workaround_limitations',
        'validation_guidance',
        'requires_write_or_restart',
        'created_by',
    ):
        assert field in response.text
    assert "method: 'POST'" in response.text
    assert 'It is not published guidance' in response.text
