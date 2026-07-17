const problemFilterForm = document.getElementById('problem-filter-form');
const problemSearch = document.getElementById('problem-search');
const problemStatusFilter = document.getElementById('problem-status-filter');
const problemOwnerFilter = document.getElementById('problem-owner-filter');
const problemList = document.getElementById('problem-list');
const clearProblemFilters = document.getElementById('clear-problem-filters');
let problemFilterTimer = null;

function normalized(value) {
  return String(value || '').trim().toLowerCase();
}

function applyProblemFilters() {
  if (!problemList) return;
  const query = normalized(problemSearch?.value);
  const status = normalized(problemStatusFilter?.value).replaceAll('_', ' ');
  const owner = normalized(problemOwnerFilter?.value);
  const cards = [...problemList.querySelectorAll('button[data-problem-id]')];
  let visible = 0;

  cards.forEach((card) => {
    const title = normalized(card.querySelector('strong')?.textContent);
    const metadata = normalized(card.querySelector('span')?.textContent);
    const problemId = normalized(card.dataset.problemId);
    const matchesQuery = !query || title.includes(query) || metadata.includes(query) || problemId.includes(query);
    const matchesStatus = !status || metadata.startsWith(`${status} ·`);
    const matchesOwner = !owner || metadata.includes(owner);
    card.hidden = !(matchesQuery && matchesStatus && matchesOwner);
    if (!card.hidden) visible += 1;
  });

  const count = document.getElementById('problem-count');
  if (count && cards.length) count.textContent = `${visible} of ${cards.length} problems`;
  problemList.dataset.filteredEmpty = visible === 0 && cards.length > 0 ? 'true' : 'false';
}

function scheduleProblemFilter() {
  window.clearTimeout(problemFilterTimer);
  problemFilterTimer = window.setTimeout(applyProblemFilters, 150);
}

problemFilterForm?.addEventListener('submit', (event) => {
  event.preventDefault();
  applyProblemFilters();
});
problemSearch?.addEventListener('input', scheduleProblemFilter);
problemOwnerFilter?.addEventListener('input', scheduleProblemFilter);
problemStatusFilter?.addEventListener('change', applyProblemFilters);
clearProblemFilters?.addEventListener('click', () => {
  problemFilterForm.reset();
  applyProblemFilters();
  problemSearch.focus();
});

if (problemList) {
  new MutationObserver(applyProblemFilters).observe(problemList, { childList: true });
}

const actionTarget = document.getElementById('problem-actions');
const actionForm = document.getElementById('action-filter-form');
const actionSearch = document.getElementById('action-search');
const actionStatus = document.getElementById('action-status-filter');
const actionType = document.getElementById('action-type-filter');
const actionOwner = document.getElementById('action-owner-filter');
const actionCount = document.getElementById('action-count');
const actionEmpty = document.getElementById('action-filter-empty');
let actionFilterTimer = null;

function actionMetadata(card) {
  const lines = [...card.querySelectorAll('p')].map((node) => node.textContent || '');
  const statusLine = lines.find((line) => line.startsWith('Status:')) || '';
  const ownerLine = lines.find((line) => line.startsWith('Owner:')) || '';
  const match = statusLine.match(/^Status:\s*(.*?)\s*·\s*Type:\s*(.*)$/);
  return {
    search: normalized(card.textContent),
    status: normalized(match?.[1]),
    type: normalized(match?.[2]),
    owner: normalized(ownerLine.replace(/^Owner:\s*/, '').split(' · ')[0]),
  };
}

function replaceActionOptions(select, values, label) {
  const current = select.value;
  select.replaceChildren(new Option(label, ''));
  [...values].sort().forEach((value) => select.append(new Option(value.replaceAll('_', ' '), value)));
  select.value = values.has(current) ? current : '';
}

function refreshActionOptions(cards) {
  replaceActionOptions(actionStatus, new Set(cards.map((card) => actionMetadata(card).status).filter(Boolean)), 'All statuses');
  replaceActionOptions(actionType, new Set(cards.map((card) => actionMetadata(card).type).filter(Boolean)), 'All types');
}

function applyActionFilters() {
  if (!actionTarget) return;
  const cards = [...actionTarget.querySelectorAll('.record-card')];
  if (!cards.length) {
    if (actionCount) actionCount.textContent = '0 actions';
    if (actionEmpty) actionEmpty.hidden = true;
    return;
  }
  const query = normalized(actionSearch?.value);
  const status = normalized(actionStatus?.value);
  const type = normalized(actionType?.value);
  const owner = normalized(actionOwner?.value);
  let visible = 0;
  cards.forEach((card) => {
    const item = actionMetadata(card);
    const matches = (!query || item.search.includes(query)) && (!status || item.status === status) && (!type || item.type === type) && (!owner || item.owner.includes(owner));
    card.hidden = !matches;
    if (matches) visible += 1;
  });
  if (actionCount) actionCount.textContent = visible === cards.length ? `${cards.length} action${cards.length === 1 ? '' : 's'}` : `${visible} of ${cards.length} actions`;
  if (actionEmpty) actionEmpty.hidden = visible !== 0;
}

function scheduleActionFilter() {
  window.clearTimeout(actionFilterTimer);
  actionFilterTimer = window.setTimeout(applyActionFilters, 150);
}

if (actionTarget && actionForm) {
  new MutationObserver(() => {
    const cards = [...actionTarget.querySelectorAll('.record-card')];
    refreshActionOptions(cards);
    applyActionFilters();
  }).observe(actionTarget, { childList: true });
  actionForm.addEventListener('submit', (event) => { event.preventDefault(); applyActionFilters(); });
  actionSearch?.addEventListener('input', scheduleActionFilter);
  actionOwner?.addEventListener('input', scheduleActionFilter);
  actionStatus?.addEventListener('change', applyActionFilters);
  actionType?.addEventListener('change', applyActionFilters);
  document.getElementById('clear-action-filters')?.addEventListener('click', () => {
    actionForm.reset();
    applyActionFilters();
    actionSearch?.focus();
  });
}
