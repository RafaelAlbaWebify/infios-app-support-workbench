[
  '/ui/static/design-system.css',
  '/ui/static/navigation.css',
  '/ui/static/shell-layout.css',
  '/ui/static/shell-content.css',
].forEach((href) => {
  const stylesheet = document.createElement('link');
  stylesheet.rel = 'stylesheet';
  stylesheet.href = href;
  document.head.append(stylesheet);
});

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

const caseLinksScript = document.createElement('script');
caseLinksScript.src = '/ui/static/case-links.js';
document.head.append(caseLinksScript);

const workAreaDefinitions = [
  { selector: '#case-catalogue-panel', id: 'work-service-context', label: 'Service context', advanced: false },
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

function createProductLink(id, href, label, description, current = false) {
  const link = document.createElement('a');
  link.id = id;
  link.href = href;
  if (current) link.setAttribute('aria-current', 'page');
  const name = document.createElement('strong');
  name.textContent = label;
  const detail = document.createElement('span');
  detail.textContent = description;
  link.append(name, detail);
  return link;
}

function buildProductShell() {
  const topbar = document.querySelector('.topbar');
  const layout = document.querySelector('main.layout');
  if (!topbar || !layout || document.querySelector('.infios-app-shell')) return;

  const shell = document.createElement('div');
  shell.className = 'infios-app-shell';
  const sidebar = document.createElement('aside');
  sidebar.className = 'infios-product-sidebar';
  sidebar.setAttribute('aria-label', 'Product navigation');
  const brand = document.createElement('div');
  brand.className = 'infios-brand';
  brand.innerHTML = '<strong>INFIOS</strong><span>Application Support Workbench</span>';
  const navigation = document.createElement('nav');
  navigation.className = 'infios-primary-nav';
  navigation.setAttribute('aria-label', 'Primary');
  navigation.append(
    createProductLink('open-incidents', '/', 'Incidents', 'Investigate and escalate', true),
    createProductLink('open-problems', '/problems', 'Problems', 'RCA and corrective actions'),
    createProductLink('open-handovers', '/handovers', 'Handovers', 'Immutable shift snapshots'),
    createProductLink('open-catalogue', '/catalogue', 'Catalogue', 'Services and dependencies'),
    createProductLink('open-analytics', '/analytics', 'Analytics', 'Descriptive operations'),
  );
  const note = document.createElement('div');
  note.className = 'infios-shell-note';
  note.innerHTML = '<strong>Evidence-led by design</strong>Context and patterns do not prove cause. Backend validation remains authoritative.';
  sidebar.append(brand, navigation, note);

  const content = document.createElement('div');
  content.className = 'infios-app-content';
  topbar.parentNode.insertBefore(shell, topbar);
  shell.append(sidebar, content);
  content.append(topbar, layout);
  document.body.classList.add('infios-shell-ready');
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

buildProductShell();
caseLinksScript.addEventListener('load', buildWorkAreaNavigation);
