const state = {
  caseId: null,
  evidenceType: null,
};

const dashboardPanel = document.querySelector('#dashboard-panel');
const createPanel = document.querySelector('#create-panel');
const casePanel = document.querySelector('#case-panel');
const caseForm = document.querySelector('#case-form');
const formError = document.querySelector('#form-error');
const evidenceEditor = document.querySelector('#evidence-editor');
const evidenceError = document.querySelector('#evidence-error');
const dashboardError = document.querySelector('#dashboard-error');

function showError(element, message) {
  element.textContent = message;
  element.hidden = false;
}

function clearError(element) {
  element.textContent = '';
  element.hidden = true;
}

function emitWorkbenchEvent(name, detail = {}) {
  window.dispatchEvent(new CustomEvent(name, { detail }));
}

async function api(path, options = {}) {
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
      // Keep the stable fallback message.
    }
    throw new Error(detail);
  }
  return response.json();
}

function setActivePanel(panel) {
  dashboardPanel.hidden = panel !== dashboardPanel;
  createPanel.hidden = panel !== createPanel;
  casePanel.hidden = panel !== casePanel;
}

function setProgress(index) {
  document.querySelectorAll('#progress-steps li').forEach((item, itemIndex) => {
    item.classList.toggle('active', itemIndex === index);
  });
}

function formatValue(value) {
  if (!value || value === 'unknown') return 'Unknown';
  return value.replaceAll('_', ' ');
}

function formatDate(value) {
  if (!value) return 'Unknown time';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Unknown time' : date.toLocaleString();
}

async function loadCases() {
  clearError(dashboardError);
  document.querySelector('#save-state').textContent = 'Loading recent cases…';
  try {
    const response = await api('/api/cases?limit=20');
    const list = document.querySelector('#recent-cases');
    if (!response.cases || response.cases.length === 0) {
      list.className = 'case-list empty-state';
      list.textContent = 'No cases found. Start a new incident to create the first one.';
      document.querySelector('#save-state').textContent = 'No saved incidents';
      return;
    }

    list.className = 'case-list';
    list.innerHTML = '';
    response.cases.forEach((supportCase) => {
      const card = document.createElement('article');
      card.className = 'case-card';
      card.tabIndex = 0;
      card.setAttribute('role', 'button');
      card.setAttribute('aria-label', `Open incident ${supportCase.title}`);

      const content = document.createElement('div');
      const title = document.createElement('h3');
      title.textContent = supportCase.title;
      const meta = document.createElement('p');
      meta.className = 'muted';
      meta.textContent = `${supportCase.application} · ${formatValue(supportCase.affected_scope)} · ${formatValue(supportCase.impact)}`;
      const updated = document.createElement('p');
      updated.className = 'case-updated';
      updated.textContent = `Updated ${formatDate(supportCase.updated_at)}`;
      content.append(title, meta, updated);

      const status = document.createElement('span');
      status.className = 'status-badge';
      status.textContent = formatValue(supportCase.status);
      card.append(content, status);

      const open = () => openCase(supportCase.case_id);
      card.addEventListener('click', open);
      card.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          open();
        }
      });
      list.append(card);
    });
    document.querySelector('#save-state').textContent = `${response.count} saved incident${response.count === 1 ? '' : 's'}`;
  } catch (error) {
    showError(dashboardError, error.message);
    document.querySelector('#save-state').textContent = 'Could not load incidents';
  }
}

async function openCase(caseId) {
  document.querySelector('#save-state').textContent = 'Opening incident…';
  try {
    const supportCase = await api(`/api/cases/${caseId}`);
    state.caseId = supportCase.case_id;
    populateCaseHeader(supportCase);
    setActivePanel(casePanel);
    setProgress(2);
    await Promise.all([loadEvidence(), loadSummary()]);
    document.querySelector('#save-state').textContent = `Opened ${supportCase.case_id}`;
    emitWorkbenchEvent('infios:case-opened', { caseId: supportCase.case_id });
  } catch (error) {
    showError(dashboardError, error.message);
    setActivePanel(dashboardPanel);
  }
}

function populateCaseHeader(supportCase) {
  document.querySelector('#case-title').textContent = supportCase.title;
  document.querySelector('#case-context').textContent = `${supportCase.application} · ${formatValue(supportCase.affected_scope)} · ${formatValue(supportCase.impact)}`;
  document.querySelector('#case-status').textContent = formatValue(supportCase.status);
  document.querySelector('#workspace-status').textContent = 'Current incident';
}

document.querySelector('#new-incident').addEventListener('click', () => {
  state.caseId = null;
  caseForm.reset();
  clearError(formError);
  setActivePanel(createPanel);
  setProgress(0);
  document.querySelector('#workspace-status').textContent = 'New incident';
  document.querySelector('#save-state').textContent = 'Not saved yet';
  document.querySelector('#application').focus();
});

document.querySelector('#cancel-create').addEventListener('click', async () => {
  setActivePanel(dashboardPanel);
  setProgress(0);
  document.querySelector('#workspace-status').textContent = 'Dashboard';
  await loadCases();
});

document.querySelector('#back-dashboard').addEventListener('click', async () => {
  evidenceEditor.hidden = true;
  clearEvidenceForm();
  setActivePanel(dashboardPanel);
  setProgress(0);
  document.querySelector('#workspace-status').textContent = 'Dashboard';
  await loadCases();
});

caseForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  clearError(formError);
  const submitButton = caseForm.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  submitButton.textContent = 'Creating incident…';

  const symptom = new FormData(caseForm).get('symptom');
  const title = document.querySelector('#title').value.trim();
  const payload = {
    application: document.querySelector('#application').value.trim(),
    title: `${title} — ${symptom}`,
    affected_scope: document.querySelector('#affected-scope').value,
    impact: document.querySelector('#impact').value,
  };

  try {
    const supportCase = await api('/api/cases', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    state.caseId = supportCase.case_id;
    populateCaseHeader(supportCase);
    document.querySelector('#save-state').textContent = `Saved as ${supportCase.case_id}`;
    setActivePanel(casePanel);
    setProgress(2);
    await Promise.all([loadEvidence(), loadSummary()]);
    emitWorkbenchEvent('infios:case-opened', { caseId: supportCase.case_id });
  } catch (error) {
    showError(formError, error.message);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = 'Create incident and continue';
  }
});

document.querySelectorAll('[data-evidence-type]').forEach((button) => {
  button.addEventListener('click', () => {
    state.evidenceType = button.dataset.evidenceType;
    document.querySelector('#evidence-heading').textContent = `Add ${button.textContent.toLowerCase()}`;
    evidenceEditor.hidden = false;
    document.querySelector('#evidence-source').focus();
  });
});

document.querySelector('#cancel-evidence').addEventListener('click', () => {
  evidenceEditor.hidden = true;
  clearEvidenceForm();
});

document.querySelector('#save-evidence').addEventListener('click', async () => {
  clearError(evidenceError);
  const source = document.querySelector('#evidence-source').value.trim();
  const content = document.querySelector('#evidence-content').value.trim();
  if (!source || !content) {
    showError(evidenceError, 'Source and observation are required.');
    return;
  }

  const button = document.querySelector('#save-evidence');
  button.disabled = true;
  button.textContent = 'Saving…';
  try {
    await api(`/api/cases/${state.caseId}/evidence`, {
      method: 'POST',
      body: JSON.stringify({
        evidence_type: state.evidenceType,
        source,
        content,
        certainty: document.querySelector('#evidence-certainty').value,
        sensitivity: 'internal',
        redacted: false,
        notes: 'Redaction review required before external sharing.',
      }),
    });
    evidenceEditor.hidden = true;
    clearEvidenceForm();
    document.querySelector('#save-state').textContent = 'Evidence saved';
    await Promise.all([loadEvidence(), loadSummary()]);
    emitWorkbenchEvent('infios:evidence-updated', { caseId: state.caseId });
  } catch (error) {
    showError(evidenceError, error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Save evidence';
  }
});

function clearEvidenceForm() {
  state.evidenceType = null;
  document.querySelector('#evidence-source').value = '';
  document.querySelector('#evidence-content').value = '';
  document.querySelector('#evidence-certainty').value = 'reported';
  clearError(evidenceError);
}

async function loadEvidence() {
  const response = await api(`/api/cases/${state.caseId}/evidence`);
  const list = document.querySelector('#evidence-list');
  document.querySelector('#evidence-count').textContent = `${response.count} item${response.count === 1 ? '' : 's'}`;
  if (!response.evidence || response.evidence.length === 0) {
    list.className = 'empty-state';
    list.textContent = 'No evidence has been added yet.';
    return;
  }

  list.className = '';
  list.innerHTML = '';
  response.evidence.forEach((item) => {
    const card = document.createElement('article');
    card.className = 'evidence-card';
    const header = document.createElement('header');
    const title = document.createElement('strong');
    title.textContent = formatValue(item.evidence_type);
    const certainty = document.createElement('span');
    certainty.className = 'muted';
    certainty.textContent = formatValue(item.certainty);
    header.append(title, certainty);

    const source = document.createElement('p');
    source.textContent = `Source: ${item.source}`;
    const content = document.createElement('p');
    content.textContent = typeof item.content === 'string' ? item.content : JSON.stringify(item.content, null, 2);
    card.append(header, source, content);
    list.append(card);
  });
}

async function loadSummary() {
  const summary = await api(`/api/cases/${state.caseId}/summary`);
  document.querySelector('#next-action').textContent = summary.next_recommended_action;
  const complete = summary.escalation_readiness.filter((item) => item.complete).length;
  document.querySelector('#known-summary').textContent = `${summary.evidence.length} evidence item(s), ${summary.observations.length} evidence-backed observation(s), and ${complete}/${summary.escalation_readiness.length} escalation checks complete.`;
  return summary;
}

document.querySelector('#refresh-summary').addEventListener('click', async () => {
  if (!state.caseId) return;
  const button = document.querySelector('#refresh-summary');
  button.disabled = true;
  button.textContent = 'Reviewing…';
  try {
    await loadSummary();
    document.querySelector('#save-state').textContent = 'Guidance refreshed';
    setProgress(3);
  } catch (error) {
    document.querySelector('#known-summary').textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = 'Review case guidance';
  }
});

loadCases();
