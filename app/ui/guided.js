const guidedState = {
  caseId: null,
  selectedCheck: null,
  actionId: null,
};

const saveState = document.querySelector('#save-state');
const actionEditor = document.querySelector('#action-result-editor');
const actionError = document.querySelector('#action-error');

async function guidedApi(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') detail = body.detail;
    } catch (_) {
      // Keep the stable fallback.
    }
    throw new Error(detail);
  }
  return response.json();
}

function setActionError(message = '') {
  actionError.textContent = message;
  actionError.hidden = !message;
}

function inferCaseId(text) {
  const match = text.match(/(?:Opened|Saved as)\s+(case-[A-Za-z0-9-]+)/i);
  return match ? match[1] : null;
}

async function refreshGuidedWorkflow() {
  if (!guidedState.caseId) return;
  await Promise.all([loadGuidedChecks(), loadDiagnosticActions()]);
}

async function loadGuidedChecks() {
  const list = document.querySelector('#guided-check-list');
  try {
    const playbook = await guidedApi(`/api/cases/${guidedState.caseId}/playbooks/post-login-feature-failure`);
    const checks = playbook.recommended_checks || [];
    document.querySelector('#check-count').textContent = `${checks.length} check${checks.length === 1 ? '' : 's'}`;
    if (checks.length === 0) {
      list.className = 'empty-state';
      list.textContent = 'No guided checks are currently available.';
      return;
    }
    list.className = 'check-list';
    list.innerHTML = '';
    checks.forEach((check) => {
      const card = document.createElement('article');
      card.className = 'check-card';
      const heading = document.createElement('div');
      const title = document.createElement('h4');
      title.textContent = check.name;
      const badge = document.createElement('span');
      badge.className = 'safety-badge';
      badge.textContent = check.safety_level.replaceAll('_', ' ');
      heading.append(title, badge);
      const purpose = document.createElement('p');
      purpose.textContent = check.purpose;
      const capture = document.createElement('p');
      capture.className = 'muted';
      capture.textContent = `Record: ${check.evidence_to_capture.join(', ')}`;
      const button = document.createElement('button');
      button.className = 'secondary';
      button.type = 'button';
      button.textContent = 'Start this safe check';
      button.addEventListener('click', () => startGuidedCheck(check, button));
      card.append(heading, purpose, capture, button);
      list.append(card);
    });
  } catch (error) {
    list.className = 'empty-state';
    list.textContent = error.message;
  }
}

async function startGuidedCheck(check, button) {
  button.disabled = true;
  button.textContent = 'Starting…';
  try {
    const action = await guidedApi(`/api/cases/${guidedState.caseId}/actions`, {
      method: 'POST',
      body: JSON.stringify({
        name: check.name,
        purpose: check.purpose,
        safety_level: check.safety_level,
        requires_write_or_restart: false,
        expected_result: check.evidence_to_capture.join(', '),
      }),
    });
    const started = await guidedApi(`/api/cases/${guidedState.caseId}/actions/${action.action_id}/start`, { method: 'POST' });
    guidedState.selectedCheck = check;
    guidedState.actionId = started.action_id;
    document.querySelector('#action-result-heading').textContent = `Record result: ${check.name}`;
    actionEditor.hidden = false;
    document.querySelector('#action-result').focus();
    saveState.textContent = 'Safe check started';
    await loadDiagnosticActions();
  } catch (error) {
    setActionError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Start this safe check';
  }
}

document.querySelector('#complete-action').addEventListener('click', async () => {
  setActionError();
  const actualResult = document.querySelector('#action-result').value.trim();
  if (!actualResult) {
    setActionError('An actual result is required before completing the check.');
    return;
  }
  const button = document.querySelector('#complete-action');
  button.disabled = true;
  button.textContent = 'Saving…';
  try {
    await guidedApi(`/api/cases/${guidedState.caseId}/actions/${guidedState.actionId}/complete`, {
      method: 'POST',
      body: JSON.stringify({
        actual_result: actualResult,
        conclusion: document.querySelector('#action-conclusion').value.trim() || null,
        performed_by: document.querySelector('#action-performed-by').value.trim() || null,
      }),
    });
    clearActionEditor();
    saveState.textContent = 'Check result saved';
    await loadDiagnosticActions();
  } catch (error) {
    setActionError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Save check result';
  }
});

document.querySelector('#cancel-action').addEventListener('click', clearActionEditor);

function clearActionEditor() {
  guidedState.selectedCheck = null;
  guidedState.actionId = null;
  actionEditor.hidden = true;
  document.querySelector('#action-result').value = '';
  document.querySelector('#action-conclusion').value = '';
  document.querySelector('#action-performed-by').value = '';
  setActionError();
}

async function loadDiagnosticActions() {
  const list = document.querySelector('#action-list');
  const response = await guidedApi(`/api/cases/${guidedState.caseId}/actions`);
  document.querySelector('#action-count').textContent = `${response.count} action${response.count === 1 ? '' : 's'}`;
  if (!response.actions || response.actions.length === 0) {
    list.className = 'empty-state';
    list.textContent = 'No diagnostic actions recorded yet.';
    return;
  }
  list.className = 'action-list';
  list.innerHTML = '';
  response.actions.forEach((action) => {
    const card = document.createElement('article');
    card.className = 'action-card';
    const heading = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = action.name;
    const status = document.createElement('span');
    status.className = 'status-badge';
    status.textContent = action.status.replaceAll('_', ' ');
    heading.append(title, status);
    const purpose = document.createElement('p');
    purpose.textContent = action.purpose;
    card.append(heading, purpose);
    if (action.actual_result) {
      const result = document.createElement('p');
      result.className = 'action-result';
      result.textContent = `Result: ${action.actual_result}`;
      card.append(result);
    }
    list.append(card);
  });
}

const observer = new MutationObserver(() => {
  const caseId = inferCaseId(saveState.textContent);
  if (caseId && caseId !== guidedState.caseId) {
    guidedState.caseId = caseId;
    refreshGuidedWorkflow();
  }
});
observer.observe(saveState, { childList: true, characterData: true, subtree: true });

document.querySelector('#refresh-summary').addEventListener('click', () => {
  window.setTimeout(refreshGuidedWorkflow, 0);
});
