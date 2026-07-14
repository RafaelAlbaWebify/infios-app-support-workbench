const databasePanel = document.createElement('details');
databasePanel.id = 'database-safety-panel';
databasePanel.className = 'work-area-disclosure';
databasePanel.innerHTML = `
  <summary><span>Database safety</span><span class="muted disclosure-hint">Integrity, backup, and restore</span></summary>
  <section class="work-area-content">
    <div class="section-heading">
      <div>
        <h3>Local database safety</h3>
        <p class="muted">Backups stay beside the configured local database. Restore always creates a verified pre-restore checkpoint.</p>
      </div>
      <span id="database-integrity-badge" class="status-badge">Not checked</span>
    </div>
    <p id="database-safety-error" class="error" role="alert" hidden></p>
    <div id="database-integrity-details" class="empty-state">Open this section to check the database.</div>
    <div class="actions">
      <button id="check-database-integrity" class="secondary" type="button">Check integrity</button>
      <button id="create-database-backup" class="primary" type="button">Create verified backup</button>
    </div>
    <div class="section-heading">
      <h4>Available backups</h4>
      <span id="database-backup-count" class="muted">0 backups</span>
    </div>
    <div id="database-backup-list" class="empty-state">No backups loaded yet.</div>
    <form id="database-restore-form" class="evidence-editor" hidden>
      <h4>Restore selected backup</h4>
      <p id="database-restore-preview" class="muted"></p>
      <div class="two-column">
        <label>Performed by<input id="database-restore-operator" required placeholder="Example: Application Support"></label>
        <label>Reason<input id="database-restore-reason" required placeholder="Example: Recover verified checkpoint"></label>
      </div>
      <label class="choice"><input id="database-restore-confirm" type="checkbox" required> I understand the current database will be replaced after an automatic pre-restore backup.</label>
      <div class="actions">
        <button class="primary" type="submit">Restore selected backup</button>
        <button id="cancel-database-restore" class="secondary" type="button">Cancel</button>
      </div>
    </form>
  </section>
`;

const dashboardPanelForDatabase = document.querySelector('#dashboard-panel');
const recentCasesForDatabase = document.querySelector('#recent-cases');
if (dashboardPanelForDatabase && recentCasesForDatabase) {
  dashboardPanelForDatabase.insertBefore(databasePanel, recentCasesForDatabase);
}

let selectedDatabaseBackup = null;

function databaseError(message = '') {
  const element = document.querySelector('#database-safety-error');
  element.textContent = message;
  element.hidden = !message;
}

function formatDatabaseBytes(value) {
  if (!Number.isFinite(value)) return 'Unknown size';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function databaseInspectionText(inspection) {
  return `${inspection.case_count} case(s) · schema ${inspection.schema_version ?? 'empty'} · ${formatDatabaseBytes(inspection.size_bytes)} · SHA-256 ${inspection.sha256.slice(0, 12)}…`;
}

async function databaseRequest(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') detail = body.detail;
    } catch (_) {
      // Keep stable fallback.
    }
    throw new Error(detail);
  }
  return response.json();
}

async function loadDatabaseIntegrity() {
  databaseError();
  const badge = document.querySelector('#database-integrity-badge');
  badge.textContent = 'Checking…';
  try {
    const inspection = await databaseRequest('/api/database/integrity');
    badge.textContent = inspection.valid ? 'Integrity OK' : 'Integrity failed';
    document.querySelector('#database-integrity-details').className = '';
    document.querySelector('#database-integrity-details').textContent = databaseInspectionText(inspection);
    return inspection;
  } catch (error) {
    badge.textContent = 'Check failed';
    databaseError(error.message);
    return null;
  }
}

async function loadDatabaseBackups() {
  databaseError();
  try {
    const response = await databaseRequest('/api/database/backups');
    const list = document.querySelector('#database-backup-list');
    document.querySelector('#database-backup-count').textContent = `${response.count} backup${response.count === 1 ? '' : 's'}`;
    if (!response.backups.length) {
      list.className = 'empty-state';
      list.textContent = 'No verified backups have been created yet.';
      return;
    }
    list.className = '';
    list.innerHTML = '';
    response.backups.forEach((backup) => {
      const card = document.createElement('article');
      card.className = 'evidence-card';
      const title = document.createElement('strong');
      title.textContent = backup.filename;
      const detail = document.createElement('p');
      detail.className = 'muted';
      detail.textContent = databaseInspectionText(backup);
      const actions = document.createElement('div');
      actions.className = 'actions';
      const restore = document.createElement('button');
      restore.type = 'button';
      restore.className = 'secondary';
      restore.textContent = 'Preview restore';
      restore.addEventListener('click', () => previewDatabaseRestore(backup.filename));
      actions.append(restore);
      card.append(title, detail, actions);
      list.append(card);
    });
  } catch (error) {
    databaseError(error.message);
  }
}

async function previewDatabaseRestore(filename) {
  databaseError();
  try {
    const preview = await databaseRequest(`/api/database/backups/${encodeURIComponent(filename)}/preview`);
    selectedDatabaseBackup = filename;
    document.querySelector('#database-restore-preview').textContent = `${filename}: ${databaseInspectionText(preview)}`;
    const form = document.querySelector('#database-restore-form');
    form.hidden = false;
    document.querySelector('#database-restore-operator').focus();
  } catch (error) {
    databaseError(error.message);
  }
}

function clearDatabaseRestoreForm() {
  selectedDatabaseBackup = null;
  const form = document.querySelector('#database-restore-form');
  form.reset();
  form.hidden = true;
  document.querySelector('#database-restore-preview').textContent = '';
}

databasePanel.addEventListener('toggle', () => {
  if (databasePanel.open) Promise.all([loadDatabaseIntegrity(), loadDatabaseBackups()]);
});

document.querySelector('#check-database-integrity').addEventListener('click', loadDatabaseIntegrity);

document.querySelector('#create-database-backup').addEventListener('click', async () => {
  const button = document.querySelector('#create-database-backup');
  button.disabled = true;
  button.textContent = 'Creating verified backup…';
  databaseError();
  try {
    const backup = await databaseRequest('/api/database/backups', {
      method: 'POST',
      body: JSON.stringify({ label: 'manual' }),
    });
    document.querySelector('#save-state').textContent = `Verified backup created: ${backup.filename}`;
    await loadDatabaseBackups();
  } catch (error) {
    databaseError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Create verified backup';
  }
});

document.querySelector('#cancel-database-restore').addEventListener('click', clearDatabaseRestoreForm);

document.querySelector('#database-restore-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!selectedDatabaseBackup) return;
  const submit = event.currentTarget.querySelector('button[type="submit"]');
  submit.disabled = true;
  submit.textContent = 'Restoring safely…';
  databaseError();
  try {
    const result = await databaseRequest('/api/database/restore', {
      method: 'POST',
      body: JSON.stringify({
        filename: selectedDatabaseBackup,
        performed_by: document.querySelector('#database-restore-operator').value.trim(),
        reason: document.querySelector('#database-restore-reason').value.trim(),
        confirm_restore: document.querySelector('#database-restore-confirm').checked,
      }),
    });
    document.querySelector('#save-state').textContent = `Database restored; rollback checkpoint ${result.pre_restore_backup.filename} created.`;
    clearDatabaseRestoreForm();
    await Promise.all([loadDatabaseIntegrity(), loadDatabaseBackups()]);
    window.setTimeout(() => window.location.reload(), 800);
  } catch (error) {
    databaseError(error.message);
  } finally {
    submit.disabled = false;
    submit.textContent = 'Restore selected backup';
  }
});
