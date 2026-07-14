const l2State = { caseId: null };
const l2SaveState = document.querySelector('#save-state');

async function l2Api(path, options = {}) {
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

function inferL2CaseId(text) {
  const match = text.match(/(?:Opened|Saved as)\s+(case-[A-Za-z0-9-]+)/i);
  return match ? match[1] : null;
}

function setL2Error(message = '') {
  const element = document.querySelector('#l2-error');
  element.textContent = message;
  element.hidden = !message;
}

function formatL2(value) {
  return value ? value.replaceAll('_', ' ') : 'unknown';
}

async function loadL2Investigation() {
  if (!l2State.caseId) return;
  const [observations, actions, explanations] = await Promise.all([
    l2Api(`/api/cases/${l2State.caseId}/observations`),
    l2Api(`/api/cases/${l2State.caseId}/actions`),
    l2Api(`/api/cases/${l2State.caseId}/explanations`),
  ]);
  renderReferenceOptions('#supporting-observations', observations.observations || [], 'observation_id', 'statement');
  renderReferenceOptions('#contradicting-observations', observations.observations || [], 'observation_id', 'statement');
  renderReferenceOptions('#validation-actions', actions.actions || [], 'action_id', 'name');
  renderExplanations(explanations.explanations || []);
}

function renderReferenceOptions(selector, items, valueKey, labelKey) {
  const select = document.querySelector(selector);
  select.innerHTML = '';
  items.forEach((item) => {
    const option = document.createElement('option');
    option.value = item[valueKey];
    option.textContent = item[labelKey];
    select.append(option);
  });
}

function selectedValues(selector) {
  return Array.from(document.querySelector(selector).selectedOptions).map((option) => option.value);
}

function renderExplanations(explanations) {
  document.querySelector('#explanation-count').textContent = `${explanations.length} explanation${explanations.length === 1 ? '' : 's'}`;
  const list = document.querySelector('#explanation-list');
  if (!explanations.length) {
    list.className = 'empty-state';
    list.textContent = 'No possible explanations recorded yet.';
    return;
  }
  list.className = '';
  list.innerHTML = '';
  explanations.forEach((item) => {
    const card = document.createElement('article');
    card.className = 'evidence-card';
    const header = document.createElement('header');
    const title = document.createElement('strong');
    title.textContent = item.statement;
    const status = document.createElement('span');
    status.className = 'status-badge';
    status.textContent = formatL2(item.status);
    header.append(title, status);
    const links = document.createElement('p');
    links.textContent = `${item.supporting_observation_ids.length} supporting · ${item.contradicting_observation_ids.length} contradicting · ${item.validation_action_ids.length} validation action(s)`;
    const controls = document.createElement('div');
    controls.className = 'actions';
    ['supported', 'weakened', 'ruled_out', 'confirmed'].forEach((nextStatus) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'secondary';
      button.textContent = formatL2(nextStatus);
      button.addEventListener('click', () => updateExplanationStatus(item.explanation_id, nextStatus));
      controls.append(button);
    });
    card.append(header, links, controls);
    list.append(card);
  });
}

async function updateExplanationStatus(explanationId, status) {
  setL2Error();
  const confirmed = status === 'confirmed';
  if (confirmed && !window.confirm('Confirm only when supporting observations exist and an operator has deliberately reviewed the evidence. Continue?')) return;
  try {
    await l2Api(`/api/cases/${l2State.caseId}/explanations/${explanationId}/status`, {
      method: 'POST',
      body: JSON.stringify({ status, confirmed_by_operator: confirmed }),
    });
    l2SaveState.textContent = `Explanation marked ${formatL2(status)}`;
    await loadL2Investigation();
  } catch (error) {
    setL2Error(error.message);
  }
}

document.querySelector('#save-explanation').addEventListener('click', async () => {
  setL2Error();
  const statement = document.querySelector('#explanation-statement').value.trim();
  if (!statement) {
    setL2Error('Describe a possible explanation without presenting it as fact.');
    return;
  }
  const button = document.querySelector('#save-explanation');
  button.disabled = true;
  button.textContent = 'Saving…';
  try {
    await l2Api(`/api/cases/${l2State.caseId}/explanations`, {
      method: 'POST',
      body: JSON.stringify({
        statement,
        supporting_observation_ids: selectedValues('#supporting-observations'),
        contradicting_observation_ids: selectedValues('#contradicting-observations'),
        validation_action_ids: selectedValues('#validation-actions'),
      }),
    });
    document.querySelector('#explanation-statement').value = '';
    l2SaveState.textContent = 'Possible explanation saved';
    await loadL2Investigation();
  } catch (error) {
    setL2Error(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Save possible explanation';
  }
});

const l2Observer = new MutationObserver(() => {
  const caseId = inferL2CaseId(l2SaveState.textContent);
  if (caseId && caseId !== l2State.caseId) {
    l2State.caseId = caseId;
    loadL2Investigation();
  }
});
l2Observer.observe(l2SaveState, { childList: true, characterData: true, subtree: true });

document.querySelector('#refresh-summary').addEventListener('click', () => {
  window.setTimeout(loadL2Investigation, 0);
});
