# TalentAI – Recruitment System

An AI-powered recruitment platform using **Logistic Regression** (pure NumPy) for resume scoring and shortlisting.

## Tech Stack
- **Backend**: Python + Flask
- **ML**: Logistic Regression (NumPy, no sklearn needed)
- **Frontend**: HTML5 + CSS3 + Vanilla JS
- **Storage**: In-memory (extendable to SQLite/Postgres)

## Quick Start

```bash
cd recruitment
pip install -r requirements.txt
python app.py
```

Then open: http://localhost:5000

## Pages
| URL | Description |
|-----|-------------|
| `/` | Landing page with live stats |
| `/apply` | Browse jobs & submit applications |
| `/admin` | Recruiter dashboard |

## ML Features (8 engineered features)
1. **Keyword Match Ratio** – % of job keywords found in resume (30% weight)
2. **Tech Skill Count** – From a list of 50+ technologies (20% weight)
3. **Years of Experience** – Extracted via regex patterns (15% weight)
4. **Education Level** – PhD=4, Masters=3, Bachelors=2, Diploma=1 (10% weight)
5. **Soft Skills** – Leadership, communication, etc. (10% weight)
6. **Quantified Achievements** – Numbers, %, $ detected (5% weight)
7. **Section Completeness** – Has education/skills/projects etc. (5% weight)
8. **Resume Length** – Word count normalized to 800 words (5% weight)

## Active Learning
- Start in **heuristic mode** (weighted dot product)
- Once you manually review 10+ applications → **Logistic Regression trains automatically**
- Model rescores all pending applicants after training

## How Scoring Works
```
features → sigmoid(W·x + b) → probability → score (0–100%)
If score ≥ job threshold → SHORTLISTED
If score < job threshold → REJECTED
```
