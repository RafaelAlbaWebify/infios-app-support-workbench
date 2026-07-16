const endpoints = {
  snapshot: '/api/analytics/operational-snapshot',
  applications: '/api/analytics/application-attention',
  actions: '/api/analytics/problem-action-workload',
  evidence: '/api/analytics/evidence-quality',
  trends: '/api/analytics/operational-trends',
  handovers: '/api/analytics/handover-activity',
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
    [item.application, item.active_case_count, item.high_severity_active_case_count, item.unassigned_active_case_count, item.blocked_or_waiting_case_count, item.active_problem_count, item.overdue_action_count, item.evidence_attention_case_count, item.cases_without_evidence_count].forEach((value) => {
      const cell = document.createElement('td');
      cell.textContent = String(value ?? 0);
      row.append(cell);
    });
    body.append(row);
  });
}

function renderTrends(report, handovers) {
  const body = document.getElementById('trend-activity-body');
  body.replaceChildren();
  setText('trend-window-label', `${report.window_days} days`);
  setText('trend-created', report.created_case_count);
  setText('trend-updated', report.updated_case_count);
  setText('trend-resolved', report.resolved_or_closed_count);
  setText('trend-handovers', handovers.total_handovers);
  const activity = (report.daily_activity || []).filter((item) => item.created || item.updated || item.resolved_or_closed);
  if (!activity.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 4;
    cell.className = 'empty-cell';
    cell.textContent = 'No case timestamp activity was recorded in this window.';
    row.append(cell);
    body.append(row);
    return;
  }
  [...activity].reverse().forEach((item) => {
    const row = document.createElement('tr');
    [item.date, item.created, item.updated, item.resolved_or_closed].forEach((value) => {
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
  const windowDays = Number(document.getElementById('analytics-window')?.value || 30);
  status.textContent = 'Loading reports…';
  error.hidden = true;
  refresh.disabled = true;
  try {
    const [snapshot, applications, actions, evidence, trends, handovers] = await Promise.all([
      fetchReport(endpoints.snapshot),
      fetchReport(endpoints.applications),
      fetchReport(endpoints.actions),
      fetchReport(endpoints.evidence),
      fetchReport(`${endpoints.trends}?window_days=${windowDays}`),
      fetchReport(`${endpoints.handovers}?window_days=${windowDays}`),
    ]);
    setText('metric-active-cases', snapshot.active_case_count);
    setText('metric-unassigned', snapshot.unassigned_active_case_count);
    setText('metric-active-problems', snapshot.active_problem_count);
    setText('metric-overdue-actions', actions.overdue_action_count);
    setText('metric-evidence-attention', evidence.cases_requiring_attention);
    renderTrends(trends, handovers);
    renderApplications(applications);
    renderSignals('action-signals', [['Active actions', actions.active_action_count], ['Overdue', actions.overdue_action_count], ['Blocked', actions.blocked_action_count], ['Awaiting validation', actions.validation_pending_action_count]]);
    renderSignals('evidence-signals', [['Cases with evidence', evidence.cases_with_evidence], ['Cases without evidence', evidence.cases_without_evidence], ['Evidence items', evidence.total_evidence_items], ['Cases with automated flags', evidence.cases_requiring_attention]]);
    status.textContent = `Reports refreshed ${new Date().toLocaleString()} for a ${windowDays}-day activity window.`;
  } catch (cause) {
    error.textContent = `Analytics could not be loaded. ${cause.message}`;
    error.hidden = false;
    status.textContent = 'Report loading failed.';
  } finally {
    refresh.disabled = false;
  }
}

document.getElementById('refresh-analytics')?.addEventListener('click', loadAnalytics);
document.getElementById('analytics-window')?.addEventListener('change', loadAnalytics);
loadAnalytics();
