const escalationState = { caseId: null };
const escalationSaveState = document.querySelector('#save-state');

async function escalationApi(path, options = {}) {
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
      // Keep fallback.
    }
    throw new Error(detail);
  }
  return response.json();
}

function inferEscalationCaseId(text) {
  const match = text.match(/(?:Opened|Saved as)\s+(case-[A-Za-z0-9-]+)/i);
  return match ? match[1] : null;
}

function setEscalationError(message = '') {
  const element = document.querySelector('#escalation-error');
  element.textContent = message;
  element.hidden = !message;
}

async function loadEscalationReadiness() {
  if (!escalationState.caseId) return;
  const summary = await escalationApi(`/api/cases/${escalationState.caseId}/summary`);
  const readiness = summary.escalation_readiness || [];
  const complete = readiness.filter((item) => item.complete).length;
  document.querySelector('#readiness-count').textContent = `${complete}/${readiness.length} ready`;
  const list = document.querySelector('#readiness-list');
  list.className = 'readiness-list';
  list.innerHTML = '';
  readiness.forEach((item) => {
    const row = document.createElement('article');
    row.className = `readiness-item ${item.complete ? 'complete' : 'missing'}`;
    const marker = document.createElement('strong');
    marker.textContent = item.complete ? 'Complete' : 'Missing';
    const content = document.createElement('div');
    const title = document.createElement('h4');
    title.textContent = item.name;
    const detail = document.createElement('p');
    detail.textContent = item.detail;
    content.append(title, detail);
    row.append(marker, content);
    list.append(row);
  });
  renderExistingEscalations(summary.escalations || []);
}

function renderExistingEscalations(escalations) {
  if (!escalations.length) return;
  renderEscalation(escalations[0]);
}

function renderEscalation(packageData) {
  const preview = document.querySelector('#escalation-preview');
  preview.className = 'escalation-preview';
  preview.innerHTML = '';
  const heading = document.createElement('div');
  const title = document.createElement('h4');
  title.textContent = `Handover for ${packageData.target_team}`;
  const meta = document.createElement('span');
  meta.className = 'muted';
  meta.textContent = packageData.package_id;
  heading.append(title, meta);
  const missing = document.createElement('p');
  missing.textContent = packageData.missing_information.length
    ? `Missing information: ${packageData.missing_information.join(' ')}`
    : 'No standard gaps detected.';
  const report = document.createElement('pre');
  report.textContent = packageData.report_text;
  const actions = document.createElement('div');
  actions.className = 'actions';
  const copy = document.createElement('button');
  copy.type = 'button';
  copy.className = 'secondary';
  copy.textContent = 'Copy handover text';
  copy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(packageData.report_text);
      copy.textContent = 'Copied';
    } catch (_) {
      copy.textContent = 'Select and copy the report';
    }
  });
  const download = document.createElement('a');
  download.className = 'text-link';
  download.textContent = 'Download Markdown';
  download.href = `/api/cases/${packageData.case_id}/escalations/${packageData.package_id}/download`;
  download.setAttribute('download', '');
  actions.append(copy, download);
  preview.append(heading, missing, report, actions);
}

document.querySelector('#generate-escalation').addEventListener('click', async () => {
  setEscalationError();
  const requestedAction = document.querySelector('#requested-action').value.trim();
  if (!requestedAction) {
    setEscalationError('Describe what the receiving team should do.');
    return;
  }
  const button = document.querySelector('#generate-escalation');
  button.disabled = true;
  button.textContent = 'Generating…';
  try {
    const packageData = await escalationApi(`/api/cases/${escalationState.caseId}/escalations`, {
      method: 'POST',
      body: JSON.stringify({
        target_team: document.querySelector('#target-team').value,
        requested_action: requestedAction,
      }),
    });
    renderEscalation(packageData);
    escalationSaveState.textContent = 'L2 handover saved';
    document.querySelectorAll('#progress-steps li').forEach((item) => item.classList.remove('active'));
    document.querySelectorAll('#progress-steps li')[4].classList.add('active');
    await loadEscalationReadiness();
  } catch (error) {
    setEscalationError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Generate L2 handover';
  }
});

const escalationObserver = new MutationObserver(() => {
  const caseId = inferEscalationCaseId(escalationSaveState.textContent);
  if (caseId && caseId !== escalationState.caseId) {
    escalationState.caseId = caseId;
    loadEscalationReadiness();
  }
});
escalationObserver.observe(escalationSaveState, { childList: true, characterData: true, subtree: true });

document.querySelector('#refresh-summary').addEventListener('click', () => {
  window.setTimeout(loadEscalationReadiness, 0);
});
