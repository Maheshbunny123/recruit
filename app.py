from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import json
import re
import pickle
import numpy as np
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = 'recruitment_secret_key'

ALLOWED_EXTENSIONS = {'pdf', 'txt', 'doc', 'docx'}

# ─── In-memory stores ────────────────────────────────────────────────────────
jobs_db = []
applicants_db = []
job_id_counter = [1]
applicant_id_counter = [1]

# ─── Logistic Regression (pure NumPy – no sklearn needed) ────────────────────
class LogisticRegressionML:
    def __init__(self):
        self.weights = None
        self.bias = 0.0
        self.is_trained = False

    def sigmoid(self, z):
        return 1 / (1 + np.exp(-np.clip(z, -500, 500)))

    def fit(self, X, y, lr=0.01, epochs=1000):
        n, d = X.shape
        self.weights = np.zeros(d)
        self.bias = 0.0
        for _ in range(epochs):
            z = X @ self.weights + self.bias
            pred = self.sigmoid(z)
            err = pred - y
            self.weights -= lr * (X.T @ err) / n
            self.bias   -= lr * np.mean(err)
        self.is_trained = True

    def predict_proba(self, X):
        return self.sigmoid(X @ self.weights + self.bias)

model = LogisticRegressionML()

# ─── Feature Engineering ─────────────────────────────────────────────────────
TECH_SKILLS = [
    'python','java','javascript','typescript','react','angular','vue','node',
    'flask','django','fastapi','sql','mysql','postgresql','mongodb','redis',
    'docker','kubernetes','aws','azure','gcp','git','linux','machine learning',
    'deep learning','tensorflow','pytorch','scikit','pandas','numpy',
    'html','css','c++','c#','rust','golang','swift','kotlin','r','matlab',
    'spark','hadoop','kafka','elasticsearch','graphql','rest','api',
    'agile','scrum','devops','ci/cd','microservices','blockchain'
]

SOFT_SKILLS = [
    'leadership','communication','teamwork','problem solving','analytical',
    'project management','time management','creativity','adaptability','critical thinking'
]

EDUCATION_KEYWORDS = {
    'phd':4,'doctorate':4,'masters':3,'mtech':3,'msc':3,'mba':3,
    'bachelors':2,'btech':2,'bsc':2,'be ':2,'b.e':2,'b.tech':2,
    'diploma':1,'certification':1,'certified':1
}

EXPERIENCE_PATTERNS = [
    r'(\d+)\+?\s*years?\s+(?:of\s+)?experience',
    r'experience\s+(?:of\s+)?(\d+)\+?\s*years?',
    r'(\d+)\+?\s*yrs?\s+(?:of\s+)?experience',
]

def extract_features(resume_text, job_keywords):
    text = resume_text.lower()
    feats = []

    # 1. Skill match ratio
    job_kw = [k.lower() for k in job_keywords]
    matched = sum(1 for k in job_kw if k in text)
    feats.append(matched / max(len(job_kw), 1))

    # 2. Tech skill count (normalised)
    tech_count = sum(1 for s in TECH_SKILLS if s in text)
    feats.append(min(tech_count / 15, 1.0))

    # 3. Soft skill count (normalised)
    soft_count = sum(1 for s in SOFT_SKILLS if s in text)
    feats.append(min(soft_count / 5, 1.0))

    # 4. Education level
    edu_score = 0
    for kw, sc in EDUCATION_KEYWORDS.items():
        if kw in text:
            edu_score = max(edu_score, sc)
    feats.append(edu_score / 4)

    # 5. Years of experience
    exp_years = 0
    for pat in EXPERIENCE_PATTERNS:
        m = re.search(pat, text)
        if m:
            exp_years = max(exp_years, int(m.group(1)))
    feats.append(min(exp_years / 10, 1.0))

    # 6. Resume length (words)
    word_count = len(text.split())
    feats.append(min(word_count / 800, 1.0))

    # 7. Has quantified achievements
    quant = len(re.findall(r'\d+%|\$\d+|\d+\s*(?:million|billion|k\b)', text))
    feats.append(min(quant / 5, 1.0))

    # 8. Section completeness
    sections = ['experience','education','skills','projects','summary','objective','certifications']
    sec_score = sum(1 for s in sections if s in text) / len(sections)
    feats.append(sec_score)

    return np.array(feats, dtype=float)

def score_resume(resume_text, job_keywords, min_experience=0):
    feats = extract_features(resume_text, job_keywords)

    if model.is_trained:
        prob = float(model.predict_proba(feats.reshape(1, -1))[0])
    else:
        # Weighted heuristic until model is trained
        weights = [0.30, 0.20, 0.10, 0.10, 0.15, 0.05, 0.05, 0.05]
        prob = float(np.dot(feats, weights))

    score = round(prob * 100, 1)

    # Penalty: experience below minimum
    exp_years = 0
    for pat in EXPERIENCE_PATTERNS:
        m = re.search(pat, resume_text.lower())
        if m:
            exp_years = max(exp_years, int(m.group(1)))
    if min_experience > 0 and exp_years < min_experience:
        score *= 0.7

    score = max(0, min(100, score))
    return score, feats.tolist()

def train_model_on_data():
    """Retrain logistic regression whenever we have enough labelled samples."""
    labelled = [a for a in applicants_db if a.get('manually_reviewed')]
    if len(labelled) < 10:
        return
    X, y = [], []
    for a in labelled:
        X.append(a['features'])
        y.append(1 if a['status'] == 'shortlisted' else 0)
    X, y = np.array(X), np.array(y)
    if len(np.unique(y)) > 1:
        model.fit(X, y)
        # Rescore pending applicants
        for a in applicants_db:
            if not a.get('manually_reviewed'):
                job = next((j for j in jobs_db if j['id'] == a['job_id']), None)
                if job:
                    sc, ft = score_resume(a['resume_text'], job['keywords'], job.get('min_experience', 0))
                    a['score'] = sc
                    a['features'] = ft

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_file_text(filepath):
    try:
        with open(filepath, 'r', errors='ignore') as f:
            return f.read()
    except:
        return ""

# ─── Routes ──────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/apply')
def apply_page():
    return render_template('apply.html')

# Jobs API
@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    return jsonify(jobs_db)

@app.route('/api/jobs', methods=['POST'])
def create_job():
    data = request.json
    job = {
        'id': job_id_counter[0],
        'title': data['title'],
        'department': data.get('department', ''),
        'location': data.get('location', ''),
        'description': data.get('description', ''),
        'keywords': [k.strip() for k in data.get('keywords', '').split(',') if k.strip()],
        'min_experience': int(data.get('min_experience', 0)),
        'min_score': float(data.get('min_score', 60)),
        'created_at': datetime.now().isoformat(),
        'status': 'active'
    }
    jobs_db.append(job)
    job_id_counter[0] += 1
    return jsonify({'success': True, 'job': job})

@app.route('/api/jobs/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    global jobs_db
    jobs_db = [j for j in jobs_db if j['id'] != job_id]
    return jsonify({'success': True})

# Applicants API
@app.route('/api/apply', methods=['POST'])
def apply():
    name = request.form.get('name', '')
    email = request.form.get('email', '')
    phone = request.form.get('phone', '')
    job_id = int(request.form.get('job_id', 0))
    cover_letter = request.form.get('cover_letter', '')

    job = next((j for j in jobs_db if j['id'] == job_id), None)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404

    resume_text = cover_letter  # fallback
    filename = None

    if 'resume' in request.files:
        file = request.files['resume']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            file_text = read_file_text(filepath)
            if file_text.strip():
                resume_text = file_text + ' ' + cover_letter

    score, features = score_resume(resume_text, job['keywords'], job.get('min_experience', 0))

    applicant = {
        'id': applicant_id_counter[0],
        'name': name,
        'email': email,
        'phone': phone,
        'job_id': job_id,
        'job_title': job['title'],
        'resume_text': resume_text,
        'resume_file': filename,
        'score': score,
        'features': features,
        'status': 'shortlisted' if score >= job['min_score'] else 'rejected',
        'applied_at': datetime.now().isoformat(),
        'manually_reviewed': False
    }
    applicants_db.append(applicant)
    applicant_id_counter[0] += 1
    train_model_on_data()

    return jsonify({
        'success': True,
        'score': score,
        'status': applicant['status'],
        'message': 'Congratulations! You have been shortlisted.' if applicant['status'] == 'shortlisted'
                   else 'Thank you for applying. We will keep your profile on file.'
    })

@app.route('/api/applicants', methods=['GET'])
def get_applicants():
    job_id = request.args.get('job_id')
    status = request.args.get('status')
    results = applicants_db[:]
    if job_id:
        results = [a for a in results if a['job_id'] == int(job_id)]
    if status:
        results = [a for a in results if a['status'] == status]
    results.sort(key=lambda x: x['score'], reverse=True)
    # Omit large resume text from list view
    safe = []
    for a in results:
        s = {k: v for k, v in a.items() if k != 'resume_text'}
        safe.append(s)
    return jsonify(safe)

@app.route('/api/applicants/<int:app_id>/status', methods=['PUT'])
def update_status(app_id):
    data = request.json
    applicant = next((a for a in applicants_db if a['id'] == app_id), None)
    if not applicant:
        return jsonify({'success': False}), 404
    applicant['status'] = data['status']
    applicant['manually_reviewed'] = True
    train_model_on_data()
    return jsonify({'success': True})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    total_jobs = len(jobs_db)
    total_apps = len(applicants_db)
    shortlisted = sum(1 for a in applicants_db if a['status'] == 'shortlisted')
    rejected = sum(1 for a in applicants_db if a['status'] == 'rejected')
    avg_score = round(np.mean([a['score'] for a in applicants_db]), 1) if applicants_db else 0
    model_status = 'Trained (Logistic Regression)' if model.is_trained else 'Heuristic Mode (needs 10+ reviewed)'
    return jsonify({
        'total_jobs': total_jobs,
        'total_applicants': total_apps,
        'shortlisted': shortlisted,
        'rejected': rejected,
        'avg_score': avg_score,
        'model_status': model_status
    })

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True, port=5000)
