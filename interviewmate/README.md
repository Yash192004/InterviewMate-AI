# 🎯 InterviewMate AI — Smart AI Interview Coach

An AI-powered interview preparation platform that personalizes every session based on your resume and adapts to your performance in real time.

---

## 🚀 Features

| Feature | Description |
|---|---|
| **AI Resume Analyzer** | Upload PDF/DOCX resume → AI extracts skills, strengths, projects, education |
| **AI Mock Interview** | HR, Technical, or Mixed interview with adaptive difficulty per session |
| **Smart Answer Evaluation** | Score 0–10 with correctness, clarity, completeness feedback + model answer |
| **Adaptive Engine** | Difficulty auto-adjusts based on your rolling performance score |
| **Personalized Study Plan** | 2-week AI-generated plan with daily tasks and curated resources |
| **Dashboard** | Charts, scores, skill breakdown, recent sessions, weak topic highlights |

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+ · Flask 3 · SQLAlchemy · SQLite
- **AI:** IBM watsonx.ai (Granite 3) · OpenAI GPT-4o-mini (fallback)
- **Frontend:** Jinja2 templates · Vanilla JS · Chart.js · Custom CSS
- **File Parsing:** pdfplumber (PDF) · python-docx (DOCX)

---

## ⚙️ Setup

### 1. Install dependencies

```bash
cd interviewmate
pip install -r requirements.txt
```

### 2. Configure AI keys

```bash
cp .env.example .env
# Edit .env and add your API keys
```

**For IBM watsonx.ai (recommended):**
1. Go to [cloud.ibm.com](https://cloud.ibm.com) → Create watsonx.ai service
2. Create a project → copy the **Project ID**
3. Go to Manage → API keys → create an **API key**
4. Set `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL` in `.env`

**For OpenAI (fallback):**
1. Go to [platform.openai.com](https://platform.openai.com/api-keys) → create API key
2. Set `OPENAI_API_KEY` in `.env`

### 3. Run

```bash
python run.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 📋 Usage Flow

1. **Upload Resume** → `/resume` → Drag & drop your resume → Click "Analyze"
2. **Start Interview** → `/interview` → Select role, type, difficulty → Start
3. **Answer Questions** → One question at a time → Get instant AI feedback
4. **View Results** → Score, topic breakdown, question-by-question review
5. **Study Plan** → `/improvement-plan` → Personalized 2-week plan with resources
6. **Dashboard** → `/dashboard` → Track progress over multiple sessions

---

## 📁 Project Structure

```
interviewmate/
├── app.py              # Flask app, all routes
├── ai_engine.py        # AI integration (watsonx.ai / OpenAI)
├── run.py              # Entry point
├── requirements.txt
├── .env.example
├── models/
│   └── database.py     # SQLAlchemy models
├── templates/
│   ├── base.html       # Sidebar + topbar layout
│   ├── dashboard.html  # Stats, charts, recent sessions
│   ├── resume.html     # Resume upload & AI analysis
│   ├── interview.html  # Setup + live interview + feedback
│   ├── results.html    # Post-interview detailed review
│   └── plan.html       # Personalized improvement plan
└── static/
    ├── css/main.css    # Premium responsive design
    └── js/
        ├── main.js     # Shared utils + Chart.js init
        ├── resume.js   # Upload, drag-drop, render analysis
        └── interview.js # Interview flow state machine
```

---

## 🔑 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `WATSONX_API_KEY` | For IBM AI | IBM Cloud API key |
| `WATSONX_PROJECT_ID` | For IBM AI | watsonx.ai project ID |
| `WATSONX_URL` | For IBM AI | Regional endpoint (default: us-south) |
| `OPENAI_API_KEY` | For OpenAI fallback | OpenAI API key |
| `SECRET_KEY` | Yes | Flask session secret |
| `PORT` | No | Port (default 5000) |

---

## 🧠 AI Architecture

```
User Resume + Job Role
        ↓
  AIEngine._llm()
  ├── IBM watsonx.ai (Granite 3 8B Instruct) ← Primary
  └── OpenAI GPT-4o-mini                     ← Fallback
        ↓
  ┌─────────────────────────┐
  │ analyze_resume()        │ → skills, strengths, roles
  │ generate_question()     │ → adaptive, topic-aware
  │ evaluate_answer()       │ → score + feedback + model answer
  │ generate_improvement_plan() → 2-week study plan
  └─────────────────────────┘
```

**Adaptive Engine logic:**
- Rolling average of last N scores → adjusts next question difficulty
- Score ≥ 7.5 → escalate to `hard`
- Score ≤ 4.0 → drop to `easy`
- Weak topics (score < 5.5) → prioritized in future questions and study plan
