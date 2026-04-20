// Tab switching
function showTab(name) {
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.snav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.currentTarget.classList.add('active');

  if (name === 'overview') loadStats();
  if (name === 'jobs') loadAdminJobs();
  if (name === 'applicants') { loadApplicants(); populateJobFilter(); }
}

// Stats
async function loadStats() {
  const d = await fetch('/api/stats').then(r => r.json());
  document.getElementById('ov-jobs').textContent = d.total_jobs;
  document.getElementById('ov-apps').textContent = d.total_applicants;
  document.getElementById('ov-short').textContent = d.shortlisted;
  document.getElementById('ov-rej').textContent = d.rejected;

  const fill = document.getElementById('asb-fill');
  const val = document.getElementById('asb-val');
  fill.style.width = d.avg_score + '%';
  val.textContent = d.avg_score + '%';

  // Model status
  const isTraned = d.model_status.includes('Trained');
  const dot = document.querySelector('.msb-dot');
  const text = document.querySelector('.msb-text');
  dot.className = 'msb-dot' + (isTraned ? ' trained' : '');
  text.textContent = d.model_status;
}

// ── Jobs ─────────────────────────────────────────────────────────────────────
let jobFormVisible = false;
function toggleJobForm() {
  jobFormVisible = !jobFormVisible;
  document.getElementById('job-form-wrap').classList.toggle('hidden', !jobFormVisible);
}

async function postJob() {
  const title = document.getElementById('jf-title').value.trim();
  const keywords = document.getElementById('jf-keywords').value.trim();
  if (!title || !keywords) { alert('Title and Keywords are required.'); return; }

  await fetch('/api/jobs', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      title,
      department: document.getElementById('jf-dept').value.trim(),
      location: document.getElementById('jf-loc').value.trim(),
      keywords,
      min_experience: document.getElementById('jf-exp').value,
      min_score: document.getElementById('jf-score').value,
      description: document.getElementById('jf-desc').value.trim()
    })
  });
  toggleJobForm();
  loadAdminJobs();
}

async function loadAdminJobs() {
  const jobs = await fetch('/api/jobs').then(r => r.json());
  const el = document.getElementById('jobs-admin-list');
  if (!jobs.length) { el.innerHTML = '<div class="empty-state">No jobs posted yet.</div>'; return; }
  el.innerHTML = jobs.map(j => `
    <div class="admin-job-card">
      <div class="ajc-info">
        <div class="ajc-title">${j.title}</div>
        <div class="ajc-meta">
          <span>🏢 ${j.department || 'General'}</span>
          <span>📍 ${j.location || 'N/A'}</span>
          <span>⏱ ${j.min_experience}+ yrs</span>
          <span>🎯 Threshold: ${j.min_score}%</span>
          <span>Keywords: ${j.keywords.join(', ')}</span>
        </div>
      </div>
      <div class="ajc-actions">
        <button class="btn-danger" onclick="deleteJob(${j.id})">Delete</button>
      </div>
    </div>
  `).join('');
}

async function deleteJob(id) {
  if (!confirm('Delete this job? Applications will remain.')) return;
  await fetch('/api/jobs/' + id, { method:'DELETE' });
  loadAdminJobs();
}

// ── Applicants ────────────────────────────────────────────────────────────────
async function populateJobFilter() {
  const jobs = await fetch('/api/jobs').then(r => r.json());
  const sel = document.getElementById('filter-job');
  sel.innerHTML = '<option value="">All Jobs</option>' +
    jobs.map(j => `<option value="${j.id}">${j.title}</option>`).join('');
}

async function loadApplicants() {
  const jobId = document.getElementById('filter-job').value;
  const status = document.getElementById('filter-status').value;
  let url = '/api/applicants?';
  if (jobId) url += 'job_id=' + jobId + '&';
  if (status) url += 'status=' + status;

  const apps = await fetch(url).then(r => r.json());
  const wrap = document.getElementById('applicants-table-wrap');

  if (!apps.length) { wrap.innerHTML = '<div class="empty-state">No applicants found.</div>'; return; }

  const scoreClass = s => s >= 70 ? 'score-high' : s >= 45 ? 'score-mid' : 'score-low';

  wrap.innerHTML = `
    <table class="app-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Name</th>
          <th>Email</th>
          <th>Job</th>
          <th>ML Score</th>
          <th>Status</th>
          <th>Applied</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        ${apps.map((a,i) => `
          <tr id="row-${a.id}">
            <td>${i+1}</td>
            <td><strong>${a.name}</strong></td>
            <td>${a.email}</td>
            <td>${a.job_title}</td>
            <td><span class="score-badge ${scoreClass(a.score)}">${a.score}%</span></td>
            <td><span class="status-pill status-${a.status}">${a.status}</span></td>
            <td>${new Date(a.applied_at).toLocaleDateString()}</td>
            <td>
              <button class="action-btn" onclick="updateStatus(${a.id},'shortlisted')">✓ Shortlist</button>
              <button class="action-btn" onclick="updateStatus(${a.id},'rejected')">✗ Reject</button>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

async function updateStatus(id, status) {
  await fetch('/api/applicants/' + id + '/status', {
    method:'PUT',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({status})
  });
  loadApplicants();
  loadStats();
}

// Init
loadStats();
