const navigationStylesheet = document.createElement('link');
navigationStylesheet.rel = 'stylesheet';
navigationStylesheet.href = '/ui/static/navigation.css';
document.head.append(navigationStylesheet);

const metadataScript = document.createElement('script');
metadataScript.src = '/ui/static/metadata.js';
document.head.append(metadataScript);

const dashboardScript = document.createElement('script');
dashboardScript.src = '/ui/static/dashboard.js';
document.head.append(dashboardScript);

const archiveScript = document.createElement('script');
archiveScript.src = '/ui/static/archive.js';
document.head.append(archiveScript);

const databaseScript = document.createElement('script');
databaseScript.src = '/ui/static/database.js';
document.head.append(databaseScript);

const workAreaDefinitions = [
  { selector: '.quick-actions', id: 'work-evidence', label: 'Evidence', advanced: false },
  { selector: '.observation-section', id: 'work-observations', label: 'Observations', advanced: false },
  { selector: '.guided-checks', id: 'work-checks', label: 'Safe checks', advanced: false },
  { selector: '.timeline-section', id: 'work-timeline', label: 'Timeline', advanced: true, open: true },
  { selector: '.l2-section', id: 'work-explanations', label: 'L2 explanations', advanced: true },
  { selector: '.escalation-section', id: 'work-escalation', label: 'Escalation', advanced: true },
  { selector: '.lifecycle-section', id: 'work-recovery', label: 'Lifecycle & recovery', advanced: true },
];

function wrapAdvancedArea(section, definition) {
  const details = document.createElement('details');
  details.className = 'work-area-disclosure';
  details.id = definition.id;
  details.open = Boolean(definition.open);
  const summary = document.createElement('summary');
  const label = document.createElement('span');
  label.textContent = definition.label;
  const hint = document.createElement('span');
  hint.className = 'muted disclosure-hint';
  hint.textContent = 'Show or hide';
  summary.append(label, hint);
  section.removeAttribute('id');
  section.classList.add('work-area-content');
  section.parentNode.insertBefore(details, section);
  details.append(summary, section);
  return details;
}

function buildWorkAreaNavigation() {
  const casePanel = document.querySelector('#case-panel');
  const summaryGrid = casePanel?.querySelector('.summary-grid');
  if (!casePanel || !summaryGrid || document.querySelector('#case-work-navigation')) return;
  const navigation = document.createElement('nav');
  navigation.id = 'case-work-navigation';
  navigation.className = 'case-work-navigation';
  navigation.setAttribute('aria-label', 'Case work areas');
  const heading = document.createElement('strong');
  heading.textContent = 'Jump to';
  const links = document.createElement('div');
  links.className = 'case-work-links';
  workAreaDefinitions.forEach((definition) => {
    const section = casePanel.querySelector(definition.selector);
    if (!section) return;
    let target = section;
    if (definition.advanced) target = wrapAdvancedArea(section, definition);
    else {
      section.id = definition.id;
      section.classList.add('work-area-anchor');
    }
    const link = document.createElement('a');
    link.href = `#${definition.id}`;
    link.textContent = definition.label;
    link.addEventListener('click', (event) => {
      event.preventDefault();
      if (target instanceof HTMLDetailsElement) target.open = true;
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      window.setTimeout(() => {
        if (target instanceof HTMLDetailsElement) target.querySelector('summary')?.focus();
        else target.querySelector('h3, h4, button, input, textarea, select')?.focus({ preventScroll: true });
      }, 250);
    });
    links.append(link);
  });
  navigation.append(heading, links);
  summaryGrid.insertAdjacentElement('afterend', navigation);
}

function addOperationalNavigation() {
  const topbar = document.querySelector('.topbar');
  const modePill = topbar?.querySelector('.mode-pill');
  if (!topbar || !modePill || document.querySelector('#open-analytics')) return;
  [
    ['open-problems', '/problems', 'Problem management'],
    ['open-analytics', '/analytics', 'Operational analytics'],
  ].forEach(([id, href, label]) => {
    const link = document.createElement('a');
    link.id = id;
    link.className = 'mode-pill';
    link.href = href;
    link.textContent = label;
    link.style.color = 'white';
    link.style.textDecoration = 'none';
    topbar.insertBefore(link, modePill);
  });
}

function updateCaseSummaryDownload(caseId) {
  const footer = document.querySelector('.footer-actions');
  if (!footer || !caseId) return;
  let link = document.querySelector('#download-case-summary');
  if (!link) {
    link = document.createElement('a');
    link.id = 'download-case-summary';
    link.className = 'text-link';
    link.textContent = 'Download case summary';
    link.setAttribute('download', '');
    footer.insertBefore(link, footer.querySelector('a[href="/docs"]'));
  }
  link.href = `/api/cases/${caseId}/summary/download`;
}

window.addEventListener('infios:case-opened', (event) => {
  updateCaseSummaryDownload(event.detail?.caseId);
});

addOperationalNavigation();
buildWorkAreaNavigation();