const originalFetch = window.fetch.bind(window);

function archiveFilterValues() {
  return {
    caseKind: document.querySelector('#case-kind-filter')?.value || 'all',
    archiveState: document.querySelector('#case-archive-filter')?.value || 'active',
    isDemo: Boolean(document.querySelector('#create-demo-case')?.checked),
  };
}

window.fetch = async (input, init = {}) => {
  const url = typeof input === 'string' ? input : input.url;
  let nextInput = input;
  let nextInit = { ...init };
  const method = (nextInit.method || 'GET').toUpperCase();

  if (method === 'GET' && url.startsWith('/api/cases?')) {
    const filters = archiveFilterValues();
    const parsed = new URL(url, window.location.origin);
    parsed.searchParams.set('case_kind', filters.caseKind);
    parsed.searchParams.set('archive_state', filters.archiveState);
    nextInput = `${parsed.pathname}?${parsed.searchParams.toString()}`;
  }

  if (method === 'POST' && url === '/api/cases' && typeof nextInit.body === 'string') {
    const payload = JSON.parse(nextInit.body);
    payload.is_demo = archiveFilterValues().isDemo;
    nextInit = { ...nextInit, body: JSON.stringify(payload) };
  }

  return originalFetch(nextInput, nextInit);
};

function triggerCaseReload() {
  document.querySelector('#case-sort')?.dispatchEvent(new Event('change'));
}

function buildDashboardArchiveFilters() {
  const form = document.querySelector('.case-filter-form');
  if (!form || document.querySelector('#case-kind-filter')) return;

  const row = document.createElement('div');
  row.className = 'two-column';
  row.innerHTML = `
    <label>Case type
      <select id="case-kind-filter">
        <option value="all">Real and demo cases</option>
        <option value="real">Real cases only</option>
        <option value="demo">Demo cases only</option>
      </select>
    </label>
    <label>Archive
      <select id="case-archive-filter">
        <option value="active">Active cases</option>
        <option value="archived">Archived cases</option>
        <option value="all">Active and archived</option>
      </select>
    </label>
  `;
  form.insertBefore(row, form.lastElementChild);
  row.querySelectorAll('select').forEach((control) => control.addEventListener('change', triggerCaseReload));

  document.querySelector('#clear-case-filters')?.addEventListener('click', () => {
    row.querySelector('#case-kind-filter').value = 'all';
    row.querySelector('#case-archive-filter').value = 'active';
  }, { capture: true });
}

function buildDemoCreationControl() {
  const form = document.querySelector('#case-form');
  if (!form || document.querySelector('#create-demo-case')) return;
  const label = document.createElement('label');
  label.className = 'choice';
  label.innerHTML = '<input id="create-demo-case" type="checkbox"> This is a public-safe demo or training incident';
  const actions = form.querySelector('.actions');
  form.insertBefore(label, actions);
}

function renderArchivePanel(supportCase) {
  const casePanel = document.querySelector('#case-panel');
  const heading = casePanel?.querySelector('.case-heading');
  if (!casePanel || !heading) return;

  let panel = document.querySelector('#case-archive-panel');
  if (!panel) {
    panel = document.createElement('section');
    panel.id = 'case-archive-panel';
    panel.className = 'evidence-editor';
    heading.insertAdjacentElement('afterend', panel);
  }

  const archived = Boolean(supportCase.archived_at);
  const history = supportCase.archive_history || [];
  panel.innerHTML = `
    <div class="section-heading">
      <div>
        <h3>${archived ? 'Archived incident' : 'Case classification and archive'}</h3>
        <p class="muted">${supportCase.is_demo ? 'Public-safe demo/training case' : 'Real operational case'}${archived ? ` · Archived ${new Date(supportCase.archived_at).toLocaleString()}` : ''}</p>
      </div>
      <span class="status-badge">${supportCase.is_demo ? 'Demo' : 'Real'}</span>
    </div>
    ${archived ? `<p><strong>Archive reason:</strong> ${supportCase.archive_reason || 'Not recorded'}</p>` : ''}
    <div class="two-column">
      <label>Performed by<input id="archive-performed-by" placeholder="Example: L1 Support"></label>
      <label>Reason<input id="archive-reason" placeholder="Explain why this case is ${archived ? 'being restored' : 'no longer active'}"></label>
    </div>
    <div class="actions"><button id="archive-action" class="secondary" type="button">${archived ? 'Restore incident' : 'Archive incident'}</button></div>
    <p id="archive-error" class="error" role="alert" hidden></p>
    <div class="section-heading"><h4>Archive history</h4><span class="muted">${history.length} event${history.length === 1 ? '' : 's'}</span></div>
    <div id="archive-history" class="${history.length ? '' : 'empty-state'}"></div>
  `;

  const historyContainer = panel.querySelector('#archive-history');
  if (!history.length) {
    historyContainer.textContent = 'This case has never been archived.';
  } else {
    history.forEach((event) => {
      const item = document.createElement('p');
      item.textContent = `${event.action} by ${event.performed_by} on ${new Date(event.occurred_at).toLocaleString()} — ${event.reason}`;
      historyContainer.append(item);
    });
  }

  panel.querySelector('#archive-action').addEventListener('click', async () => {
    const performedBy = panel.querySelector('#archive-performed-by').value.trim();
    const reason = panel.querySelector('#archive-reason').value.trim();
    const error = panel.querySelector('#archive-error');
    if (!performedBy || !reason) {
      error.textContent = 'Performed by and reason are required.';
      error.hidden = false;
      return;
    }
    error.hidden = true;
    const button = panel.querySelector('#archive-action');
    button.disabled = true;
    try {
      const action = archived ? 'restore' : 'archive';
      const response = await originalFetch(`/api/cases/${supportCase.case_id}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ performed_by: performedBy, reason }),
      });
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail || `Request failed with status ${response.status}`);
      }
      document.querySelector('#save-state').textContent = archived ? 'Incident restored' : 'Incident archived';
      document.querySelector('#back-dashboard')?.click();
    } catch (requestError) {
      error.textContent = requestError.message;
      error.hidden = false;
      button.disabled = false;
    }
  });
}

window.addEventListener('infios:case-opened', async (event) => {
  const caseId = event.detail?.caseId;
  if (!caseId) return;
  const response = await originalFetch(`/api/cases/${caseId}`);
  if (response.ok) renderArchivePanel(await response.json());
});

buildDashboardArchiveFilters();
buildDemoCreationControl();
