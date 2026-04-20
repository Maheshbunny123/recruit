let currentJobId = null;

// Load jobs
async function loadJobs() {
  const res = await fetch('/api/jobs');
  const jobs = await res.json();
  const grid = document.getElementById('jobs-list');

  if (!jobs.length) {
    grid.innerHTML = '<div class="loading-state">No open positions right now. Check back soon!</div>';
    return;
  }

  // Populate job filter in apply page
  grid.innerHTML = jobs.map(j => `
    <div class="job-card">
      <div class="job-title">${j.title}</div>
      <div class="job-meta">
        <span class="job-tag">🏢 ${j.department || 'General'}</span>
        <span class="job-tag">📍 ${j.location || 'N/A'}</span>
        <span class="job-tag">⏱ ${j.min_experience}+ yrs</span>
      </div>
      <div class="job-keywords">
        ${j.keywords.slice(0,6).map(k => `<span class="kw-chip">${k}</span>`).join('')}
        ${j.keywords.length > 6 ? `<span class="kw-chip">+${j.keywords.length-6} more</span>` : ''}
      </div>
      <div class="job-desc">${(j.description || 'Click below to learn more and apply.').substring(0,120)}…</div>
      <div class="job-threshold">Shortlist threshold: ${j.min_score}%</div>
      <button class="btn-primary" onclick="openApply(${j.id}, '${j.title.replace(/'/g,"\\'")}')">Apply Now →</button>
    </div>
  `).join('');
}

function openApply(jobId, title) {
  currentJobId = jobId;
  document.getElementById('modal-job-title').textContent = title;
  document.getElementById('form-job-id').value = jobId;
  document.getElementById('apply-form').classList.remove('hidden');
  document.getElementById('result-panel').classList.add('hidden');
  document.getElementById('apply-modal').classList.remove('hidden');
  document.getElementById('apply-form').reset();
  document.getElementById('file-name').textContent = 'No file chosen';
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  document.getElementById('apply-modal').classList.add('hidden');
  document.body.style.overflow = '';
}

// File drop handling
const drop = document.getElementById('file-drop');
const fileInput = document.getElementById('resume-input');

drop.addEventListener('click', () => fileInput.click());
drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('drag-over'); });
drop.addEventListener('dragleave', () => drop.classList.remove('drag-over'));
drop.addEventListener('drop', e => {
  e.preventDefault();
  drop.classList.remove('drag-over');
  if (e.dataTransfer.files[0]) {
    fileInput.files = e.dataTransfer.files;
    document.getElementById('file-name').textContent = e.dataTransfer.files[0].name;
  }
});
fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) document.getElementById('file-name').textContent = fileInput.files[0].name;
});

// Form submit
document.getElementById('apply-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('submit-btn');
  btn.innerHTML = '<span>⏳ Scoring with ML…</span>';
  btn.disabled = true;

  const fd = new FormData(e.target);

  try {
    const res = await fetch('/api/apply', { method:'POST', body:fd });
    const data = await res.json();

    if (data.success) {
      showResult(data);
    } else {
      alert(data.error || 'Submission failed.');
      btn.innerHTML = '<span>Submit Application</span>';
      btn.disabled = false;
    }
  } catch {
    alert('Network error. Please try again.');
    btn.innerHTML = '<span>Submit Application</span>';
    btn.disabled = false;
  }
});

function showResult(data) {
  document.getElementById('apply-form').classList.add('hidden');
  const panel = document.getElementById('result-panel');
  panel.classList.remove('hidden');

  const score = data.score;
  const isShort = data.status === 'shortlisted';

  // Animate score
  const numEl = document.getElementById('result-score-num');
  const ring = document.getElementById('progress-ring');
  const circumference = 326.7;
  ring.style.stroke = isShort ? '#22c55e' : '#ef4444';

  let current = 0;
  const target = score;
  const interval = setInterval(() => {
    current = Math.min(current + 1.5, target);
    numEl.textContent = Math.round(current) + '%';
    const offset = circumference - (current / 100) * circumference;
    ring.style.strokeDashoffset = offset;
    if (current >= target) clearInterval(interval);
  }, 16);

  const badge = document.getElementById('result-status-badge');
  badge.textContent = isShort ? '✓ Shortlisted' : '✗ Not Shortlisted';
  badge.className = 'result-status ' + data.status;

  document.getElementById('result-message').textContent = data.message;
}

loadJobs();
