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
