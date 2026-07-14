const lifecycleState = { caseId: null, evidence: [] };
const lifecycleSaveState = document.querySelector('#save-state');

async function lifecycleApi(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') detail = body.detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return response.json();
}

function inferLifecycleCaseId(text) {
  const match = text.match(/(?:Opened|Saved as)\s+(case-[A-Za-z0-9-]+)/i);
  return match ? match[1] : null;
}

function setLifecycleError(message = '') {
  const element = document.querySelector('#lifecycle-error');
  element.textContent = message;
  element.hidden = !message;
}

async function loadLifecycle() {
  if (!lifecycleState.caseId) return;
  const [supportCase, evidenceResponse, recoveryResponse] = await Promise.all([
    lifecycleApi(`/api/cases/${lifecycleState.caseId}`),
    lifecycleApi(`/api/cases/${lifecycleState.caseId}/evidence`),
    lifecycleApi(`/api/cases/${lifecycleState.caseId}/recovery-validations`),
  ]);
  lifecycleState.evidence = evidenceResponse.evidence || [];
  document.querySelector('#case-status').textContent = supportCase.status.replaceAll('_', ' ');
  document.querySelector('#lifecycle-status').textContent = supportCase.status.replaceAll('_', ' ');
  const select = document.querySelector('#next-status');
  select.value = '';
  Array.from(select.options).forEach((option) => {
    option.hidden = option.dataset.from && !option.dataset.from.split(',').includes(supportCase.status);
  });
  renderRecoveryEvidence();
  renderRecoveries(recoveryResponse.validations || []);
}

function renderRecoveryEvidence() {
  const select = document.querySelector('#recovery-evidence');
  select.innerHTML = '';
  lifecycleState.evidence.forEach((item) => {
    const option = document.createElement('option');
    option.value = item.evidence_id;
    option.textContent = `${item.evidence_type.replaceAll('_', ' ')} — ${item.source}`;
    select.append(option);
  });
}

function renderRecoveries(validations) {
  const container = document.querySelector('#recovery-list');
  document.querySelector('#recovery-count').textContent = `${validations.length} validation${validations.length === 1 ? '' : 's'}`;
  if (!validations.length) {
    container.className = 'empty-state';
    container.textContent = 'No recovery validation recorded yet.';
    return;
  }
  container.className = '';
  container.innerHTML = '';
  validations.forEach((item) => {
    const card = document.createElement('article');
    card.className = 'evidence-card';
    const title = document.createElement('strong');
    title.textContent = `${item.outcome.replaceAll('_', ' ')} — ${item.method}`;
    const result = document.createElement('p');
    result.textContent = item.result;
    const meta = document.createElement('p');
    meta.className = 'muted';
    meta.textContent = `Performed by ${item.performed_by}`;
    card.append(title, result, meta);
    container.append(card);
  });
}

document.querySelector('#change-status').addEventListener('click', async () => {
  setLifecycleError();
  const status = document.querySelector('#next-status').value;
  if (!status) return setLifecycleError('Select a valid next status.');
  try {
    const supportCase = await lifecycleApi(`/api/cases/${lifecycleState.caseId}/status`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    });
    lifecycleSaveState.textContent = `Status changed to ${supportCase.status.replaceAll('_', ' ')}`;
    await loadLifecycle();
  } catch (error) {
    setLifecycleError(error.message);
  }
});

document.querySelector('#save-recovery').addEventListener('click', async () => {
  setLifecycleError();
  const outcome = document.querySelector('#recovery-outcome').value;
  const method = document.querySelector('#recovery-method').value.trim();
  const result = document.querySelector('#recovery-result').value.trim();
  const performedBy = document.querySelector('#recovery-performed-by').value.trim();
  const evidenceIds = Array.from(document.querySelector('#recovery-evidence').selectedOptions).map((option) => option.value);
  if (!method || !result || !performedBy) return setLifecycleError('Method, result, and performed by are required.');
  if (outcome === 'passed' && evidenceIds.length === 0) return setLifecycleError('Passed recovery validation requires supporting evidence.');
  try {
    await lifecycleApi(`/api/cases/${lifecycleState.caseId}/recovery-validations`, {
      method: 'POST',
      body: JSON.stringify({
        outcome,
        method,
        result,
        performed_by: performedBy,
        evidence_ids: evidenceIds,
      }),
    });
    lifecycleSaveState.textContent = 'Recovery validation saved';
    await loadLifecycle();
  } catch (error) {
    setLifecycleError(error.message);
  }
});

const lifecycleObserver = new MutationObserver(() => {
  const caseId = inferLifecycleCaseId(lifecycleSaveState.textContent);
  if (caseId && caseId !== lifecycleState.caseId) {
    lifecycleState.caseId = caseId;
    loadLifecycle();
  }
});
lifecycleObserver.observe(lifecycleSaveState, { childList: true, characterData: true, subtree: true });

document.querySelector('#refresh-summary').addEventListener('click', () => window.setTimeout(loadLifecycle, 0));
