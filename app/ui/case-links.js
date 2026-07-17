function label(value) { return String(value || 'unknown').replaceAll('_', ' '); }

function ensurePanel() {
  const anchor = document.querySelector('#case-panel .summary-grid');
  if (!anchor) return null;
  let panel = document.querySelector('#case-catalogue-panel');
  if (panel) return panel;
  panel = document.createElement('section');
  panel.id = 'case-catalogue-panel';
  panel.className = 'observation-section';
  panel.innerHTML = '<div class="section-heading"><div><p class="step-label">Operational context</p><h3>Services and dependencies</h3><p class="muted">Explicit catalogue links recorded for this case.</p></div><span id="case-catalogue-status" class="status-badge">Not loaded</span></div><p id="case-catalogue-error" class="error" hidden></p><div id="case-catalogue-list" class="empty-state">Open an incident to load catalogue context.</div><p class="muted">Catalogue relationships provide investigation and ownership context only; they do not prove that a dependency caused the incident.</p>';
  anchor.insertAdjacentElement('afterend', panel);
  return panel;
}

async function loadCaseLinks(caseId) {
  if (!caseId || !ensurePanel()) return;
  const status = document.querySelector('#case-catalogue-status');
  const list = document.querySelector('#case-catalogue-list');
  const error = document.querySelector('#case-catalogue-error');
  status.textContent = 'Loading';
  error.hidden = true;
  try {
    const response = await fetch(`/api/catalogue/cases/${caseId}/dependency-context`);
    const report = await response.json();
    if (!response.ok) throw new Error(report.detail || `HTTP ${response.status}`);
    status.textContent = label(report.status);
    list.replaceChildren();
    if (!report.linked_services?.length) {
      list.className = 'empty-state';
      list.textContent = 'No catalogue services are explicitly linked to this incident.';
      return;
    }
    list.className = 'action-list';
    report.linked_services.forEach((item) => {
      const card = document.createElement('article');
      card.className = 'action-card';
      const related = (item.related_services || []).map((entry) => `${label(entry.direction)}: ${entry.service.name}`).join('; ') || 'No directly recorded dependencies.';
      card.innerHTML = '<div><strong></strong><span class="status-badge"></span></div><p></p><p></p><p class="muted"></p>';
      card.querySelector('strong').textContent = item.service.name;
      card.querySelector('span').textContent = label(item.link.role);
      const lines = card.querySelectorAll('p');
      lines[0].textContent = `${label(item.service.kind)} · Owner: ${item.service.owner_team || 'Unknown'}`;
      lines[1].textContent = `Link reason: ${item.link.reason}`;
      lines[2].textContent = related;
      list.append(card);
    });
  } catch (cause) {
    status.textContent = 'Unavailable';
    error.textContent = `Catalogue context could not be loaded. ${cause.message}`;
    error.hidden = false;
    list.className = 'empty-state';
    list.textContent = 'No catalogue context is currently available.';
  }
}

ensurePanel();
window.addEventListener('infios:case-opened', (event) => loadCaseLinks(event.detail?.caseId));