const endpoints = {
  snapshot: '/api/analytics/operational-snapshot',
  applications: '/api/analytics/application-attention',
  actions: '/api/analytics/problem-action-workload',
  evidence: '/api/analytics/evidence-quality',
};

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = String(value ?? 0);
}

function signalRow(label, value) {
  const term = document.createElement('dt');
  term.textContent = label;
  const description = document.createElement('dd');
  description.textContent = String(value ?? 0);
  return [term, description];
}

function renderSignals(targetId, rows) {
  const target = document.getElementById(targetId);
  target.replaceChildren();
  rows.forEach(([label, value]) => target.append(...signalRow(label, value)));
}

function renderApplications(report) {
  const body = document.getElementById('application-attention-body');
  body.replaceChildren();
  const applications = report.applications || [];
  setText('application-count', `${applications.length} application${applications.length === 1 ? '' : 's'}`);
  if (!applications.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 9;
    cell.className = 'empty-cell';
    cell.textContent = 'No real case applications are currently recorded.';
    row.append(cell);
    body.append(row);
    return;
  }
  applications.forEach((item) => {
    const row = document.createElement('tr');
    [
      item.application,
      item.active_case_count,
      item.high_severity_active_case_count,
      item.unassigned_active_case_count,
      item.blocked_or_waiting_case_count,
      item.active_problem_count,
      item.overdue_action_count,
      item.evidence_attention_case_count,
      item.cases_without_evidence_count,
    ].forEach((value) => {
      const cell = document.createElement('td');
      cell.textContent = String(value ?? 0);
      row.append(cell);
    });
    body.append(row);
  });
}

async function fetchReport(url) {
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`${url} returned HTTP ${response.status}`);
  return response.json();
}

async function loadAnalytics() {
  const status = document.getElementById('analytics-status');
  const error = document.getElementById('analytics-error');
  const refresh = document.getElementById('refresh-analytics');
  status.textContent = 'Loading reports…';
  error.hidden = true;
  refresh.disabled = true;
  try {
    const [snapshot, applications, actions, evidence] = await Promise.all([
      fetchReport(endpoints.snapshot),
      fetchReport(endpoints.applications),
      fetchReport(endpoints.actions),
      fetchReport(endpoints.evidence),
    ]);
    setText('metric-active-cases', snapshot.active_case_count);
    setText('metric-unassigned', snapshot.unassigned_active_case_count);
    setText('metric-active-problems', snapshot.active_problem_count);
    setText('metric-overdue-actions', actions.overdue_action_count);
    setText('metric-evidence-attention', evidence.cases_requiring_attention);
    renderApplications(applications);
    renderSignals('action-signals', [
      ['Active actions', actions.active_action_count],
      ['Overdue', actions.overdue_action_count],
      ['Blocked', actions.blocked_action_count],
      ['Awaiting validation', actions.validation_pending_action_count],
    ]);
    renderSignals('evidence-signals', [
      ['Cases with evidence', evidence.cases_with_evidence],
      ['Cases without evidence', evidence.cases_without_evidence],
      ['Evidence items', evidence.total_evidence_items],
      ['Cases with automated flags', evidence.cases_requiring_attention],
    ]);
    status.textContent = `Reports refreshed ${new Date().toLocaleString()}.`;
  } catch (cause) {
    error.textContent = `Analytics could not be loaded. ${cause.message}`;
    error.hidden = false;
    status.textContent = 'Report loading failed.';
  } finally {
    refresh.disabled = false;
  }
}

document.getElementById('refresh-analytics')?.addEventListener('click', loadAnalytics);
loadAnalytics();
