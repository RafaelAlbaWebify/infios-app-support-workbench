const state = {
  caseId: null,
  evidenceType: null,
};

const caseForm = document.querySelector('#case-form');
const createPanel = document.querySelector('#create-panel');
const casePanel = document.querySelector('#case-panel');
const formError = document.querySelector('#form-error');
const evidenceEditor = document.querySelector('#evidence-editor');
const evidenceError = document.querySelector('#evidence-error');

function showError(element, message) {
  element.textContent = message;
  element.hidden = false;
}

function clearError(element) {
  element.textContent = '';
  element.hidden = true;
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
    document.querySelector('#case-title').textContent = supportCase.title;
    document.querySelector('#case-context').textContent = `${supportCase.application} · ${supportCase.affected_scope} · ${supportCase.impact}`;
    document.querySelector('#case-status').textContent = supportCase.status.replaceAll('_', ' ');
    document.querySelector('#save-state').textContent = `Saved as ${supportCase.case_id}`;
    createPanel.hidden = true;
    casePanel.hidden = false;
    document.querySelectorAll('#progress-steps li')[0].classList.remove('active');
    document.querySelectorAll('#progress-steps li')[2].classList.add('active');
    await loadEvidence();
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
    await loadEvidence();
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
    title.textContent = item.evidence_type.replaceAll('_', ' ');
    const certainty = document.createElement('span');
    certainty.className = 'muted';
    certainty.textContent = item.certainty.replaceAll('_', ' ');
    header.append(title, certainty);

    const source = document.createElement('p');
    source.textContent = `Source: ${item.source}`;
    const content = document.createElement('p');
    content.textContent = typeof item.content === 'string' ? item.content : JSON.stringify(item.content, null, 2);
    card.append(header, source, content);
    list.append(card);
  });
}

document.querySelector('#refresh-summary').addEventListener('click', async () => {
  if (!state.caseId) return;
  const button = document.querySelector('#refresh-summary');
  button.disabled = true;
  button.textContent = 'Reviewing…';
  try {
    const summary = await api(`/api/cases/${state.caseId}/summary`);
    document.querySelector('#next-action').textContent = summary.next_recommended_action;
    const complete = summary.escalation_readiness.filter((item) => item.complete).length;
    document.querySelector('#known-summary').textContent = `${summary.evidence.length} evidence item(s), ${summary.observations.length} evidence-backed observation(s), and ${complete}/${summary.escalation_readiness.length} escalation checks complete.`;
    document.querySelector('#save-state').textContent = 'Guidance refreshed';
    document.querySelectorAll('#progress-steps li').forEach((item) => item.classList.remove('active'));
    document.querySelectorAll('#progress-steps li')[3].classList.add('active');
  } catch (error) {
    document.querySelector('#known-summary').textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = 'Review case guidance';
  }
});
