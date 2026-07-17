const guidanceTarget = document.getElementById('problem-known-errors');
const guidanceForm = document.getElementById('known-error-filter-form');
const guidanceSearch = document.getElementById('known-error-search');
const guidanceStatus = document.getElementById('known-error-status-filter');
const guidanceSafety = document.getElementById('known-error-safety-filter');
const guidanceOwner = document.getElementById('known-error-owner-filter');
const guidanceCount = document.getElementById('known-error-count');
const guidanceEmpty = document.getElementById('known-error-filter-empty');
let guidanceTimer = null;

function guidanceNormalized(value) {
  return String(value || '').trim().toLowerCase();
}

function guidanceMetadata(card) {
  const lines = [...card.querySelectorAll('p')].map((node) => node.textContent || '');
  const first = lines.find((line) => line.startsWith('Status:')) || '';
  const ownerLine = lines.find((line) => line.startsWith('Owner:')) || '';
  const match = first.match(/^Status:\s*(.*?)\s*·\s*Safety:\s*(.*)$/);
  return {
    search: guidanceNormalized(card.textContent),
    status: guidanceNormalized(match?.[1]),
    safety: guidanceNormalized(match?.[2]),
    owner: guidanceNormalized(ownerLine.replace(/^Owner:\s*/, '')),
  };
}

function guidanceOptions(select, values, label) {
  const current = select.value;
  select.replaceChildren(new Option(label, ''));
  [...values].sort().forEach((value) => select.append(new Option(value.replaceAll('_', ' '), value)));
  select.value = values.has(current) ? current : '';
}

function applyGuidanceFilters() {
  if (!guidanceTarget) return;
  const cards = [...guidanceTarget.querySelectorAll('.record-card')];
  if (!cards.length) {
    guidanceCount.textContent = '0 records';
    guidanceEmpty.hidden = true;
    return;
  }
  const query = guidanceNormalized(guidanceSearch.value);
  const status = guidanceNormalized(guidanceStatus.value);
  const safety = guidanceNormalized(guidanceSafety.value);
  const owner = guidanceNormalized(guidanceOwner.value);
  let visible = 0;
  cards.forEach((card) => {
    const item = guidanceMetadata(card);
    const matches = (!query || item.search.includes(query)) && (!status || item.status === status) && (!safety || item.safety === safety) && (!owner || item.owner.includes(owner));
    card.hidden = !matches;
    if (matches) visible += 1;
  });
  guidanceCount.textContent = visible === cards.length ? `${cards.length} record${cards.length === 1 ? '' : 's'}` : `${visible} of ${cards.length} records`;
  guidanceEmpty.hidden = visible !== 0;
}

function refreshGuidanceList() {
  const cards = [...guidanceTarget.querySelectorAll('.record-card')];
  guidanceOptions(guidanceStatus, new Set(cards.map((card) => guidanceMetadata(card).status).filter(Boolean)), 'All statuses');
  guidanceOptions(guidanceSafety, new Set(cards.map((card) => guidanceMetadata(card).safety).filter(Boolean)), 'All safety levels');
  applyGuidanceFilters();
}

if (guidanceTarget && guidanceForm) {
  new MutationObserver(refreshGuidanceList).observe(guidanceTarget, { childList: true });
  guidanceForm.addEventListener('submit', (event) => { event.preventDefault(); applyGuidanceFilters(); });
  [guidanceSearch, guidanceOwner].forEach((control) => control.addEventListener('input', () => {
    window.clearTimeout(guidanceTimer);
    guidanceTimer = window.setTimeout(applyGuidanceFilters, 150);
  }));
  [guidanceStatus, guidanceSafety].forEach((control) => control.addEventListener('change', applyGuidanceFilters));
  document.getElementById('clear-known-error-filters').addEventListener('click', () => {
    guidanceForm.reset();
    applyGuidanceFilters();
    guidanceSearch.focus();
  });
  refreshGuidanceList();
}
