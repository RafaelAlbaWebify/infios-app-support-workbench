const traceState = { caseId: null, evidence: [] };
const traceSaveState = document.querySelector('#save-state');

async function traceApi(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') detail = body.detail;
      else if (body.detail && body.detail.message) detail = body.detail.message;
    } catch (_) {
      // Keep fallback.
    }
    throw new Error(detail);
  }
  return response.json();
}

function inferTraceCaseId(text) {
  const match = text.match(/(?:Opened|Saved as)\s+(case-[A-Za-z0-9-]+)/i);
  return match ? match[1] : null;
}

function setTraceError(message = '') {
  const element = document.querySelector('#observation-error');
  element.textContent = message;
  element.hidden = !message;
}

function formatTraceValue(value) {
  return value ? value.replaceAll('_', ' ') : 'unknown';
}

async function loadTraceability() {
  if (!traceState.caseId) return;
  const [evidenceResponse, observationResponse, timelineResponse] = await Promise.all([
    traceApi(`/api/cases/${traceState.caseId}/evidence`),
    traceApi(`/api/cases/${traceState.caseId}/observations`),
    traceApi(`/api/cases/${traceState.caseId}/timeline`),
  ]);
  traceState.evidence = evidenceResponse.evidence || [];
  renderEvidenceChoices(traceState.evidence);
  renderObservations(observationResponse.observations || []);
  renderTimeline(timelineResponse.events || []);
}

function renderEvidenceChoices(evidence) {
  const select = document.querySelector('#observation-evidence');
  select.innerHTML = '';
  evidence.forEach((item) => {
    const option = document.createElement('option');
    option.value = item.evidence_id;
    option.textContent = `${formatTraceValue(item.evidence_type)} — ${item.source}`;
    select.append(option);
  });
  if (!evidence.length) {
    const option = document.createElement('option');
    option.disabled = true;
    option.textContent = 'Add evidence before creating an observation';
    select.append(option);
  }
}

function renderObservations(observations) {
  document.querySelector('#observation-count').textContent = `${observations.length} observation${observations.length === 1 ? '' : 's'}`;
  const list = document.querySelector('#observation-list');
  if (!observations.length) {
    list.className = 'empty-state';
    list.textContent = 'No evidence-backed observations recorded yet.';
    return;
  }
  list.className = '';
  list.innerHTML = '';
  observations.forEach((item) => {
    const card = document.createElement('article');
    card.className = 'evidence-card';
    const header = document.createElement('header');
    const category = document.createElement('strong');
    category.textContent = formatTraceValue(item.category);
    const certainty = document.createElement('span');
    certainty.className = 'muted';
    certainty.textContent = formatTraceValue(item.certainty);
    header.append(category, certainty);
    const statement = document.createElement('p');
    statement.textContent = item.statement;
    const references = document.createElement('p');
    references.className = 'muted';
    references.textContent = `Supported by ${item.evidence_ids.length} evidence item(s)`;
    card.append(header, statement, references);
    list.append(card);
  });
}

function renderTimeline(events) {
  document.querySelector('#timeline-count').textContent = `${events.length} event${events.length === 1 ? '' : 's'}`;
  const list = document.querySelector('#timeline-list');
  if (!events.length) {
    list.className = 'empty-state';
    list.textContent = 'No timeline events available.';
    return;
  }
  list.className = 'timeline-list';
  list.innerHTML = '';
  events.forEach((event) => {
    const row = document.createElement('article');
    row.className = 'timeline-item';
    const time = document.createElement('time');
    time.textContent = event.timestamp ? new Date(event.timestamp).toLocaleString() : 'Unknown time';
    const content = document.createElement('div');
    const type = document.createElement('strong');
    type.textContent = formatTraceValue(event.event_type);
    const summary = document.createElement('p');
    summary.textContent = event.summary;
    const meta = document.createElement('span');
    meta.className = 'muted';
    meta.textContent = `${formatTraceValue(event.timestamp_precision)} time · ${formatTraceValue(event.certainty)}`;
    content.append(type, summary, meta);
    row.append(time, content);
    list.append(row);
  });
}

document.querySelector('#save-observation').addEventListener('click', async () => {
  setTraceError();
  const statement = document.querySelector('#observation-statement').value.trim();
  const selectedEvidence = Array.from(document.querySelector('#observation-evidence').selectedOptions).map((option) => option.value);
  if (!statement) {
    setTraceError('Write a factual observation supported by the selected evidence.');
    return;
  }
  if (!selectedEvidence.length) {
    setTraceError('Select at least one evidence item from this case.');
    return;
  }
  const button = document.querySelector('#save-observation');
  button.disabled = true;
  button.textContent = 'Saving…';
  try {
    await traceApi(`/api/cases/${traceState.caseId}/observations`, {
      method: 'POST',
      body: JSON.stringify({
        statement,
        category: document.querySelector('#observation-category').value,
        evidence_ids: selectedEvidence,
        certainty: document.querySelector('#observation-certainty').value,
      }),
    });
    document.querySelector('#observation-statement').value = '';
    traceSaveState.textContent = 'Evidence-backed observation saved';
    await loadTraceability();
    window.dispatchEvent(new CustomEvent('infios:observation-updated', { detail: { caseId: traceState.caseId } }));
  } catch (error) {
    setTraceError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Save observation';
  }
});

const traceObserver = new MutationObserver(() => {
  const caseId = inferTraceCaseId(traceSaveState.textContent);
  if (caseId && caseId !== traceState.caseId) {
    traceState.caseId = caseId;
    loadTraceability();
  }
});
traceObserver.observe(traceSaveState, { childList: true, characterData: true, subtree: true });

window.addEventListener('infios:case-opened', (event) => {
  traceState.caseId = event.detail.caseId;
  loadTraceability();
});

window.addEventListener('infios:evidence-updated', (event) => {
  if (event.detail.caseId === traceState.caseId) loadTraceability();
});

document.querySelector('#refresh-summary').addEventListener('click', () => {
  window.setTimeout(loadTraceability, 0);
});
