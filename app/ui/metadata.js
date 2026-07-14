const metadataState = { caseId: null, supportCase: null };

const metadataSection = document.createElement('section');
metadataSection.className = 'metadata-section';
metadataSection.innerHTML = `
  <div class="section-heading">
    <div>
      <h3>Case details</h3>
      <p class="muted">Update operational metadata without changing evidence, observations, or lifecycle state.</p>
    </div>
    <button id="edit-case-metadata" class="secondary" type="button">Edit case details</button>
  </div>
  <div id="case-metadata-summary" class="summary-grid"></div>
  <form id="case-metadata-form" class="evidence-editor" hidden>
    <div class="two-column">
      <label>Title<input id="metadata-title" required></label>
      <label>Application<input id="metadata-application" required></label>
      <label>Environment<input id="metadata-environment" required></label>
      <label>Severity<input id="metadata-severity" required></label>
      <label>Owner<input id="metadata-owner" placeholder="Unassigned"></label>
      <label>Affected scope<input id="metadata-scope" required></label>
    </div>
    <label>Impact<input id="metadata-impact" required></label>
    <label>Changed by<input id="metadata-changed-by" required placeholder="Example: L1 Support"></label>
    <div class="actions">
      <button class="primary" type="submit">Save case details</button>
      <button id="cancel-case-metadata" class="secondary" type="button">Cancel</button>
    </div>
    <p id="metadata-error" class="error" role="alert" hidden></p>
  </form>
  <div class="section-heading"><h4>Change history</h4><span id="metadata-history-count" class="muted">0 changes</span></div>
  <div id="metadata-history" class="empty-state">No case-detail changes recorded yet.</div>
`;

document.querySelector('#case-panel .summary-grid')?.insertAdjacentElement('afterend', metadataSection);

function metadataError(message = '') {
  const element = document.querySelector('#metadata-error');
  element.textContent = message;
  element.hidden = !message;
}

function metadataValue(value) {
  return value || 'Unassigned';
}

function renderMetadata(supportCase) {
  metadataState.supportCase = supportCase;
  const summary = document.querySelector('#case-metadata-summary');
  summary.innerHTML = '';
  [
    ['Application', supportCase.application],
    ['Environment', supportCase.environment],
    ['Severity', supportCase.severity],
    ['Owner', metadataValue(supportCase.owner)],
    ['Affected scope', supportCase.affected_scope],
    ['Impact', supportCase.impact],
  ].forEach(([label, value]) => {
    const card = document.createElement('article');
    const heading = document.createElement('strong');
    heading.textContent = label;
    const text = document.createElement('p');
    text.textContent = value;
    card.append(heading, text);
    summary.append(card);
  });

  const history = supportCase.metadata_changes || [];
  document.querySelector('#metadata-history-count').textContent = `${history.length} change${history.length === 1 ? '' : 's'}`;
  const list = document.querySelector('#metadata-history');
  if (!history.length) {
    list.className = 'empty-state';
    list.textContent = 'No case-detail changes recorded yet.';
    return;
  }
  list.className = 'action-list';
  list.innerHTML = '';
  [...history].reverse().forEach((change) => {
    const card = document.createElement('article');
    card.className = 'action-card';
    const title = document.createElement('strong');
    title.textContent = change.summary;
    const meta = document.createElement('p');
    meta.className = 'muted';
    meta.textContent = `${change.changed_by} · ${new Date(change.changed_at).toLocaleString()}`;
    card.append(title, meta);
    list.append(card);
  });
}

function populateMetadataForm() {
  const supportCase = metadataState.supportCase;
  document.querySelector('#metadata-title').value = supportCase.title;
  document.querySelector('#metadata-application').value = supportCase.application;
  document.querySelector('#metadata-environment').value = supportCase.environment;
  document.querySelector('#metadata-severity').value = supportCase.severity;
  document.querySelector('#metadata-owner').value = supportCase.owner || '';
  document.querySelector('#metadata-scope').value = supportCase.affected_scope;
  document.querySelector('#metadata-impact').value = supportCase.impact;
}

async function metadataApi(path, options = {}) {
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

window.addEventListener('infios:case-opened', async (event) => {
  metadataState.caseId = event.detail?.caseId;
  if (!metadataState.caseId) return;
  const supportCase = await metadataApi(`/api/cases/${metadataState.caseId}`);
  renderMetadata(supportCase);
});

document.querySelector('#edit-case-metadata').addEventListener('click', () => {
  populateMetadataForm();
  metadataError();
  document.querySelector('#case-metadata-form').hidden = false;
  document.querySelector('#metadata-title').focus();
});

document.querySelector('#cancel-case-metadata').addEventListener('click', () => {
  document.querySelector('#case-metadata-form').hidden = true;
  metadataError();
});

document.querySelector('#case-metadata-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  metadataError();
  const button = event.currentTarget.querySelector('button[type="submit"]');
  button.disabled = true;
  button.textContent = 'Saving…';
  try {
    const supportCase = await metadataApi(`/api/cases/${metadataState.caseId}`, {
      method: 'PATCH',
      body: JSON.stringify({
        title: document.querySelector('#metadata-title').value.trim(),
        application: document.querySelector('#metadata-application').value.trim(),
        environment: document.querySelector('#metadata-environment').value.trim(),
        severity: document.querySelector('#metadata-severity').value.trim(),
        owner: document.querySelector('#metadata-owner').value.trim() || null,
        affected_scope: document.querySelector('#metadata-scope').value.trim(),
        impact: document.querySelector('#metadata-impact').value.trim(),
        changed_by: document.querySelector('#metadata-changed-by').value.trim(),
      }),
    });
    renderMetadata(supportCase);
    document.querySelector('#case-title').textContent = supportCase.title;
    document.querySelector('#case-context').textContent = `${supportCase.application} · ${supportCase.affected_scope} · ${supportCase.impact}`;
    document.querySelector('#case-metadata-form').hidden = true;
    document.querySelector('#save-state').textContent = 'Case details updated';
  } catch (error) {
    metadataError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Save case details';
  }
});
