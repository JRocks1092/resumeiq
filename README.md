<div align="center">

# 🧠 ResumeIQ

**AI-Powered Resume Analysis & Job Matching Platform**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![Celery](https://img.shields.io/badge/Celery-5.6-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Ollama](https://img.shields.io/badge/Ollama-Local_AI-000000?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

*A full-stack recruitment platform that leverages local AI to analyse resumes, rank candidates, and match job seekers to open vacancies — all running privately on your own hardware.*

---

</div>

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [API Reference](#-api-reference)
- [Page Routes](#-page-routes)
- [Project Structure](#-project-structure)
- [AI Pipelines](#-ai-pipelines)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🔍 Overview

**ResumeIQ** is a Django-based platform designed for HR teams and job candidates. It provides two core AI-driven workflows:

1. **Resume Analysis** — HR admins create job vacancies, candidates apply by uploading their resume PDFs, and the system uses a local Ollama LLM to produce detailed analysis reports with scores, strengths, improvement areas, keyword analysis, and ranked applicant lists.

2. **Resume–Vacancy Matching** — Candidates upload their resume once and instantly see all open vacancies ranked by fit score (0–100) with a plain-English summary per job. No application is created — it's a pure discovery tool.

All AI inference runs **locally** via [Ollama](https://ollama.com), ensuring full data privacy — no resume data ever leaves your machine.

---

## ✨ Features

### For Candidates
- 🔐 Secure registration & JWT-based authentication
- 📄 Browse available job vacancies
- 📤 Upload resume PDF and apply to vacancies
- 📊 View application status tracking (`pending` → `processing` → `analysed`)
- 🎯 **Match My Resume** — one-click matching against all open vacancies with ranked results and color-coded scores
- 📋 View personal application history

### For HR Admins
- 📝 Create, edit, and manage job vacancies
- 👥 View all applicants per vacancy with AI-generated rankings
- 📈 Detailed AI analysis reports per applicant:
  - Overall score & rating
  - Strengths & areas to improve
  - Section-by-section breakdown
  - Keyword analysis
  - Project & experience evaluation
  - Final summary
- 📊 Dashboard with recruitment overview

### Platform
- 🤖 Local AI inference via Ollama (no external API calls)
- ⚡ Asynchronous processing with Celery + Redis
- 🔒 Role-based access control (Candidate / HR)
- 📱 Responsive UI with mobile support
- 🔑 JWT authentication with token refresh

---

## 🏗 Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Browser   │◄───►│  Django App  │◄───►│   SQLite    │
│  (Templates │     │  (REST API)  │     │  Database   │
│  + JS)      │     └──────┬───────┘     └─────────────┘
└─────────────┘            │
                           │ task.delay()
                           ▼
                    ┌──────────────┐     ┌─────────────┐
                    │   Celery     │◄───►│   Redis     │
                    │   Worker     │     │  (Broker +  │
                    └──────┬───────┘     │   Results)  │
                           │             └─────────────┘
                           │ HTTP
                           ▼
                    ┌──────────────┐
                    │   Ollama     │
                    │  (Local LLM) │
                    └──────────────┘
```

**Key design decisions:**
- **Celery** handles all AI tasks asynchronously (Ollama processes one request at a time)
- **Redis** serves as both the Celery message broker and result backend
- Match results are stored in Redis with a **10-minute TTL** — no database writes for matching
- Resume PDFs for matching are processed **in-memory only** (never saved to disk)
- Resume PDFs for applications are stored under `media/resumes/`

---

## 🛠 Tech Stack

| Layer          | Technology                                                    |
|----------------|---------------------------------------------------------------|
| **Backend**    | Django 6.0, Django REST Framework 3.17                        |
| **Auth**       | JWT via `djangorestframework-simplejwt`                       |
| **Task Queue** | Celery 5.6 + Redis                                           |
| **AI/LLM**     | Ollama (local) — default model: `gemma4:31b-cloud`            |
| **PDF Parsing**| PyMuPDF (`fitz`)                                              |
| **Database**   | SQLite (development)                     |
| **Frontend**   | Django Templates + JavaScript + Tailwind CSS                  |
| **HTTP Client**| HTTPX (for Ollama API calls)                                  |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Redis** server running locally
- **Ollama** installed with a model pulled (e.g., `ollama pull gemma4:31b-cloud`)

### 1. Clone the Repository

```bash
git clone https://github.com/jidukrishna/resumeiq.git
cd resumeiq
```

### 2. Create & Activate Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```


### 4. Run Migrations

```bash
python manage.py migrate
```

### 5. Create a Superuser (optional)

```bash
python manage.py createsuperuser
```

### 6. Start the Services

**Terminal 1 — Django Development Server:**
```bash
python manage.py runserver
```

**Terminal 2 — Celery Worker:**
```bash
celery -A resumeanalyser worker --loglevel=info
```

**Terminal 3 — Redis (if not already running):**
```bash
redis-server
```

**Terminal 4 — Ollama (if not already running):**
```bash
ollama serve
```

The application will be available at **http://localhost:8000**

---

## 🔐 Environment Variables

Create a `.env` file in the project root (see `.env.example`):

| Variable         | Description                        | Default                      |
|------------------|------------------------------------|------------------------------|
| `SECRET_KEY`     | Django secret key                  | *(required)*                 |
| `DEBUG`          | Debug mode                         | `True`                       |
| `ALLOWED_HOSTS`  | Comma-separated allowed hosts      | `localhost,127.0.0.1`        |
| `REDIS_URL`      | Redis connection URL               | `redis://localhost:6379/0`   |
| `MEDIA_URL`      | URL prefix for media files         | `/media/`                    |
| `MEDIA_ROOT`     | Filesystem path for media files    | `media/`                     |

Ollama settings are configured in `resumeanalyser/settings.py`:
- `OLLAMA_MODEL` — the model to use (default: `gemma4:31b-cloud`)
- `OLLAMA_URL` — Ollama server URL (default: `http://localhost:11434`)
- `OLLAMA_THINK` — enable/disable thinking mode (default: `False`)

---

## 📡 API Reference

### Authentication

| Method | Endpoint               | Description               | Auth     |
|--------|------------------------|---------------------------|----------|
| POST   | `/api/auth/register/`  | Register a new user       | None     |
| POST   | `/api/auth/login/`     | Login (returns JWT)       | None     |
| POST   | `/api/auth/refresh/`   | Refresh access token      | None     |

### User Profile

| Method     | Endpoint          | Description            | Auth        |
|------------|-------------------|------------------------|-------------|
| GET        | `/api/users/me/`  | Get current user       | Bearer JWT  |
| PATCH      | `/api/users/me/`  | Update profile         | Bearer JWT  |

### Vacancies

| Method         | Endpoint                          | Description                      | Auth          |
|----------------|-----------------------------------|----------------------------------|---------------|
| GET            | `/api/vacancies/`                 | List all vacancies               | Public        |
| POST           | `/api/vacancies/`                 | Create a vacancy                 | HR only       |
| GET            | `/api/vacancies/available/`       | List open vacancies              | Authenticated |
| GET            | `/api/vacancies/{id}/`            | Get vacancy details              | Public        |
| PUT / PATCH    | `/api/vacancies/{id}/`            | Update a vacancy                 | HR only       |
| DELETE         | `/api/vacancies/{id}/`            | Delete a vacancy                 | HR only       |
| GET            | `/api/vacancies/{id}/applicants/` | Ranked applicant list            | HR only       |

### Resume–Vacancy Matching

| Method | Endpoint                         | Description                      | Auth           |
|--------|----------------------------------|----------------------------------|----------------|
| POST   | `/api/vacancies/match/`          | Upload PDF, start matching       | Candidate only |
| GET    | `/api/vacancies/match/{task_id}/`| Poll match results               | Candidate only |

### Applications

| Method | Endpoint                          | Description                    | Auth           |
|--------|-----------------------------------|--------------------------------|----------------|
| POST   | `/api/applications/`              | Submit application + resume    | Candidate only |
| GET    | `/api/applications/list/`         | List user's applications       | Authenticated  |
| GET    | `/api/applications/{id}/`         | Application details            | Authenticated  |
| PATCH  | `/api/applications/{id}/status/`  | Update application status      | HR only        |

### Analytics

| Method | Endpoint                          | Description                    | Auth    |
|--------|-----------------------------------|--------------------------------|---------|
| GET    | `/api/analytics/{application_id}/`| AI analysis results            | HR only |

---

## 🗺 Page Routes

### Authentication
| Path           | Page               |
|----------------|--------------------|
| `/`            | Login              |
| `/register/`   | Registration       |

### Candidate Pages
| Path                    | Page                           |
|-------------------------|--------------------------------|
| `/vacancies/`           | Browse vacancies               |
| `/vacancies/{id}/`      | Vacancy detail                 |
| `/match/`               | Resume–Vacancy matching tool   |
| `/my-applications/`     | Application history            |

### HR Pages
| Path                              | Page                        |
|-----------------------------------|-----------------------------|
| `/hr/dashboard/`                  | HR dashboard                |
| `/hr/vacancies/`                  | Vacancy management          |
| `/hr/vacancies/create/`           | Create new vacancy          |
| `/hr/vacancies/{id}/edit/`        | Edit vacancy                |
| `/hr/vacancies/{id}/applicants/`  | Ranked applicant list       |
| `/hr/applications/{id}/`         | Applicant detail + analysis |

---

## 📁 Project Structure

```
resume_final/
├── manage.py                    # Django CLI entry point
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (git-ignored)
├── .env.example                 # Environment template
├── db.sqlite3                   # SQLite database (git-ignored)
│
├── resumeanalyser/              # Django project configuration
│   ├── settings.py              #   Main settings (DB, auth, Celery, Ollama)
│   ├── urls.py                  #   Root URL routing
│   ├── celery.py                #   Celery app initialization
│   ├── wsgi.py                  #   WSGI entry point
│   └── asgi.py                  #   ASGI entry point
│
├── users/                       # User management app
│   ├── models.py                #   Custom User model (UUID PK, email login)
│   ├── serializers.py           #   Registration & profile serializers
│   ├── views.py                 #   Auth views + profile API
│   ├── permissions.py           #   IsHR / IsCandidate permission classes
│   ├── urls.py                  #   API URL routing
│   └── urls_pages.py            #   Template page routing
│
├── vacancies/                   # Vacancy management app
│   ├── models.py                #   Vacancy model
│   ├── serializers.py           #   Vacancy serializers
│   ├── views.py                 #   CRUD views + matching API views
│   ├── match_utils.py           #   PDF extraction, prompt builder, Ollama caller
│   ├── match_tasks.py           #   Celery task for resume–vacancy matching
│   ├── urls.py                  #   API URL routing
│   └── urls_pages.py            #   Template page routing
│
├── applications/                # Application submission app
│   ├── models.py                #   Application model (status tracking)
│   ├── serializers.py           #   Application create/list serializers
│   ├── views.py                 #   Submit, list, detail API views
│   ├── tasks.py                 #   Celery task for AI resume analysis
│   ├── urls.py                  #   API URL routing
│   └── urls_pages.py            #   Template page routing
│
├── analytics/                   # AI analysis results app
│   ├── models.py                #   Analytics model (scores, breakdowns)
│   ├── serializers.py           #   Analytics serializers
│   ├── views.py                 #   Analytics & ranked applicant views
│   ├── urls.py                  #   API URL routing
│   └── urls_pages.py            #   Template page routing
│
├── templates/                   # Django HTML templates
│   ├── base.html                #   Base layout with navbar
│   ├── auth/                    #   Login & registration pages
│   ├── candidate/               #   Candidate-facing pages
│   └── hr/                      #   HR-facing pages
│
└── media/                       # Uploaded files (git-ignored)
    └── resumes/                 #   Candidate resume PDFs
```

---

## 🤖 AI Pipelines

### Pipeline 1: Resume Analysis (per application)

```
Candidate uploads PDF  →  Application created  →  Celery task queued
                                                         │
                                                         ▼
                                                   Extract PDF text
                                                         │
                                                         ▼
                                                   Build AI prompt
                                                   (vacancy + resume)
                                                         │
                                                         ▼
                                                   Call Ollama LLM
                                                         │
                                                         ▼
                                                   Parse JSON response
                                                         │
                                                         ▼
                                                   Save Analytics record
                                                   (score, strengths, etc.)
```

**Output:** Stored in the `Analytics` model — overall score, rating, strengths, areas to improve, section breakdown, keyword analysis, projects, experience, and final summary.

### Pipeline 2: Resume–Vacancy Matching (exploration)

```
Candidate uploads PDF  →  Extract text in memory  →  Celery task queued
                           (never saved to disk)           │
                                                           ▼
                                                     Fetch all open vacancies
                                                           │
                                                           ▼
                                                     Build single prompt
                                                     (all jobs + resume)
                                                           │
                                                           ▼
                                                     Call Ollama LLM (once)
                                                           │
                                                           ▼
                                                     Parse & sort results
                                                     by match_score DESC
                                                           │
                                                           ▼
                                                     Store in Redis (10min TTL)
                                                     → Frontend polls & renders
```

**Output:** Temporary results in Redis — ranked vacancy cards with match score (0–100) and summary. Color-coded: 🟢 ≥80, 🟡 ≥50, 🔴 <50.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ using Django, Celery & Ollama**

</div>

