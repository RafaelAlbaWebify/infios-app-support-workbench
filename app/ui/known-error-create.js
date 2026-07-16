function showKnownErrorCreate() {
  const panel = document.getElementById('known-error-create');
  document.getElementById('known-error-review').hidden = true;
  panel.hidden = false;
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideKnownErrorCreate() {
  document.getElementById('known-error-create-form').reset();
  document.getElementById('known-error-create').hidden = true;
}

function updateDraftSafety() {
  const requiresChange = document.getElementById('known-error-write-restart').checked;
  const safety = document.getElementById('known-error-safety');
  if (requiresChange && safety.value === 'read_only') safety.value = 'approved_change_required';
  safety.querySelector('option[value="read_only"]').disabled = requiresChange;
}

async function submitKnownErrorDraft(event) {
  event.preventDefault();
  if (!selectedProblemId) return;
  const error = document.getElementById('problem-error');
  error.hidden = true;
  const steps = document.getElementById('known-error-steps').value.split('\n').map((value) => value.trim()).filter(Boolean);
  const body = {
    title: document.getElementById('known-error-title').value.trim(),
    symptom_summary: document.getElementById('known-error-symptoms').value.trim(),
    workaround_steps: steps,
    workaround_limitations: document.getElementById('known-error-limitations').value.trim(),
    validation_guidance: document.getElementById('known-error-validation').value.trim(),
    safety: document.getElementById('known-error-safety').value,
    requires_write_or_restart: document.getElementById('known-error-write-restart').checked,
    owner: document.getElementById('known-error-owner').value.trim(),
    created_by: document.getElementById('known-error-created-by').value.trim(),
  };
  text('problem-status-message', 'Saving known-error draft…');
  try {
    await requestJson(`/api/problems/${selectedProblemId}/known-errors`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    hideKnownErrorCreate();
    await openProblem(selectedProblemId);
    text('problem-status-message', 'Known-error draft saved. It is not published guidance.');
  } catch (cause) {
    error.textContent = `Known-error draft was not saved. ${cause.message}`;
    error.hidden = false;
    text('problem-status-message', 'Known-error draft blocked.');
  }
}

document.getElementById('open-known-error-create')?.addEventListener('click', showKnownErrorCreate);
document.getElementById('cancel-known-error-create')?.addEventListener('click', hideKnownErrorCreate);
document.getElementById('known-error-write-restart')?.addEventListener('change', updateDraftSafety);
document.getElementById('known-error-create-form')?.addEventListener('submit', submitKnownErrorDraft);
