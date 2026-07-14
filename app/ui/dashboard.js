const dashboardCounters = document.createElement('section');
dashboardCounters.className = 'summary-grid';
dashboardCounters.setAttribute('aria-label', 'Operational case counters');
dashboardCounters.innerHTML = `
  <article><strong>Open</strong><p id="counter-open">0</p></article>
  <article><strong>Waiting or blocked</strong><p id="counter-waiting">0</p></article>
  <article><strong>Escalated</strong><p id="counter-escalated">0</p></article>
  <article><strong>Recovery validation</strong><p id="counter-recovery">0</p></article>
  <article><strong>Resolved today</strong><p id="counter-resolved">0</p></article>
`;

document.querySelector('#dashboard-panel .case-heading')?.insertAdjacentElement('afterend', dashboardCounters);

async function loadDashboardCounters() {
  try {
    const response = await fetch('/api/cases/dashboard');
    if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
    const counts = await response.json();
    document.querySelector('#counter-open').textContent = counts.open_cases;
    document.querySelector('#counter-waiting').textContent = counts.waiting_cases;
    document.querySelector('#counter-escalated').textContent = counts.escalated_cases;
    document.querySelector('#counter-recovery').textContent = counts.recovery_validation_cases;
    document.querySelector('#counter-resolved').textContent = counts.resolved_today;
  } catch (error) {
    dashboardCounters.setAttribute('data-load-error', error.message);
  }
}

window.addEventListener('infios:case-opened', loadDashboardCounters);
document.querySelector('#back-dashboard')?.addEventListener('click', loadDashboardCounters);
document.querySelector('#cancel-create')?.addEventListener('click', loadDashboardCounters);
loadDashboardCounters();
