from app.analyzer import analyze_incident
from app.main import load_sample


def test_403_safe_next_steps_do_not_repeat_generic_login_guidance() -> None:
    incident = load_sample("incident-403-after-login.json")
    result = analyze_incident(incident)

    known_working_user_steps = [
        step for step in result.safe_next_steps if "known working user" in step.lower()
    ]

    assert len(known_working_user_steps) == 1
    assert not any(
        step == "Confirm whether credentials are accepted before the error appears."
        for step in result.safe_next_steps
    )
    assert any("access error" in step.lower() for step in result.safe_next_steps)


def test_escalation_note_does_not_duplicate_sentence_punctuation() -> None:
    incident = load_sample("incident-500-login.json")
    result = analyze_incident(incident)

    assert ".." not in result.escalation_note
    assert "Impact:" in result.escalation_note
    assert "Observed symptom:" in result.escalation_note


def test_403_rca_keeps_access_control_uncertainty_visible() -> None:
    incident = load_sample("incident-403-after-login.json")
    result = analyze_incident(incident)

    assert "confirmed root cause is not yet known" in result.rca_draft
    assert "access-control failure" in result.rca_draft
    assert "authorization rule" in result.rca_draft
