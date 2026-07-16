let selectedProblemId = null;
let problemRecords = [];

async function requestJson(url, options = {}) {
  const response = await fetch(url, { headers: { Accept: 'application/json', ...(options.headers || {}) }, ...options });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail;
    const message = typeof detail === 'string' ? detail : detail?.message || `${url} returned HTTP ${response.status}`;
    const blockers = detail?.blockers?.length ? `: ${detail.blockers.join(', ')}` : '';
    throw new Error(`${message}${blockers}`);
  }
  return payload;
}

function text(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = String(value ?? '');
}

function readable(value) {
  return String(value || 'unknown').replaceAll('_', ' ');
}

function renderProblemList() {
  const target = document.getElementById('problem-list');
  target.replaceChildren();
  text('problem-count', `${problemRecords.length} problem${problemRecords.length === 1 ? '' : 's'}`);
  if (!problemRecords.length) {
    target.className = 'problem-list empty-state';
    target.textContent = 'No problem records are currently stored.';
    document.getElementById('problem-detail').hidden = true;
    return;
  }
  target.className = 'problem-list';
  problemRecords.forEach((problem) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.problemId = problem.problem_id;
    button.setAttribute('aria-current', problem.problem_id === selectedProblemId ? 'true' : 'false');
    const title = document.createElement('strong');
    title.textContent = problem.title;
    const meta = document.createElement('span');
    meta.textContent = `${readable(problem.status)} · ${problem.occurrence_count ?? problem.case_ids?.length ?? 0} occurrences · ${problem.owner}`;
    button.append(title, meta);
    button.addEventListener('click', () => openProblem(problem.problem_id));
    target.append(button);
  });
}

function renderCards(targetId, items, render) {
  const target = document.getElementById(targetId);
  target.replaceChildren();
  if (!items.length) {
    target.className = 'empty-state';
    target.textContent = targetId === 'problem-rca' ? 'No RCA statements.' : 'No corrective actions.';
    return;
  }
  target.className = 'record-list';
  items.forEach((item) => target.append(render(item)));
}

function recordCard(title, lines) {
  const article = document.createElement('article');
  article.className = 'record-card';
  const heading = document.createElement('strong');
  heading.textContent = title;
  article.append(heading);
  lines.forEach((line) => {
    const paragraph = document.createElement('p');
    paragraph.textContent = line;
    article.append(paragraph);
  });
  return article;
}

function renderHistory(history) {
  const target = document.getElementById('problem-history');
  target.replaceChildren();
  if (!history.length) {
    target.className = 'empty-state';
    target.textContent = 'No status transitions recorded.';
    return;
  }
  target.className = 'record-list';
  [...history].reverse().forEach((event) => {
    target.append(recordCard(`${readable(event.from_status)} → ${readable(event.to_status)}`, [
      `${event.changed_by} · ${new Date(event.changed_at).toLocaleString()}`,
      event.reason,
    ]));
  });
}

function renderReadiness(report) {
  text('readiness-state', report.ready_for_operator_review ? 'Ready for operator review' : 'Not ready');
  const blockers = document.getElementById('readiness-blockers');
  blockers.replaceChildren();
  if (!report.blockers?.length) {
    const item = document.createElement('li');
    item.textContent = 'No readiness blockers are currently recorded.';
    blockers.append(item);
    return;
  }
  report.blockers.forEach((blocker) => {
    const item = document.createElement('li');
    item.textContent = readable(blocker);
    blockers.append(item);
  });
}

async function openProblem(problemId) {
  selectedProblemId = problemId;
  renderProblemList();
  const detail = document.getElementById('problem-detail');
  const error = document.getElementById('problem-error');
  error.hidden = true;
  text('problem-status-message', 'Loading selected problem…');
  try {
    const [problem, rca, actions, readiness] = await Promise.all([
      requestJson(`/api/problems/${problemId}`),
      requestJson(`/api/problems/${problemId}/rca`),
      requestJson(`/api/problems/${problemId}/actions`),
      requestJson(`/api/problems/${problemId}/closure-readiness`),
    ]);
    text('problem-title', problem.title);
    text('problem-summary', problem.summary);
    text('problem-current-status', readable(problem.status));
    text('problem-owner', problem.owner);
    text('problem-cases', (problem.case_ids || []).join(', '));
    text('problem-occurrences', problem.occurrence_count ?? problem.case_ids?.length ?? 0);
    renderCards('problem-rca', rca.statements || [], (item) => recordCard(item.statement, [
      `Status: ${readable(item.status)}`,
      `Supporting explanations: ${item.supporting_explanation_ids?.length || 0}`,
    ]));
    renderCards('problem-actions', actions.actions || [], (item) => recordCard(item.title, [
      `Status: ${readable(item.status)} · Type: ${readable(item.action_type)}`,
      `Owner: ${item.owner}${item.due_date ? ` · Due: ${item.due_date}` : ''}`,
    ]));
    renderReadiness(readiness);
    renderHistory(problem.status_history || []);
    document.getElementById('new-problem-status').value = '';
    detail.hidden = false;
    text('problem-status-message', `Problem ${problem.problem_id} loaded.`);
  } catch (cause) {
    error.textContent = `Problem details could not be loaded. ${cause.message}`;
    error.hidden = false;
    text('problem-status-message', 'Problem detail loading failed.');
  }
}

async function loadProblems({ preserveSelection = true } = {}) {
  const error = document.getElementById('problem-error');
  const refresh = document.getElementById('refresh-problems');
  error.hidden = true;
  refresh.disabled = true;
  text('problem-status-message', 'Loading problem records…');
  try {
    const report = await requestJson('/api/problems?active_only=false');
    problemRecords = report.problems || [];
    if (!preserveSelection || !problemRecords.some((item) => item.problem_id === selectedProblemId)) {
      selectedProblemId = problemRecords[0]?.problem_id || null;
    }
    renderProblemList();
    if (selectedProblemId) await openProblem(selectedProblemId);
    else text('problem-status-message', 'No problem records found.');
  } catch (cause) {
    error.textContent = `Problem records could not be loaded. ${cause.message}`;
    error.hidden = false;
    text('problem-status-message', 'Problem loading failed.');
  } finally {
    refresh.disabled = false;
  }
}

async function submitStatusChange(event) {
  event.preventDefault();
  if (!selectedProblemId) return;
  const error = document.getElementById('problem-error');
  error.hidden = true;
  const body = {
    to_status: document.getElementById('new-problem-status').value,
    changed_by: document.getElementById('problem-changed-by').value.trim(),
    reason: document.getElementById('problem-change-reason').value.trim(),
  };
  text('problem-status-message', 'Saving audited status change…');
  try {
    await requestJson(`/api/problems/${selectedProblemId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    document.getElementById('problem-status-form').reset();
    await loadProblems({ preserveSelection: true });
    text('problem-status-message', 'Status change saved with operator audit details.');
  } catch (cause) {
    error.textContent = `Status change was not saved. ${cause.message}`;
    error.hidden = false;
    text('problem-status-message', 'Status change blocked.');
  }
}

document.getElementById('refresh-problems')?.addEventListener('click', () => loadProblems());
document.getElementById('problem-status-form')?.addEventListener('submit', submitStatusChange);
loadProblems({ preserveSelection: false });