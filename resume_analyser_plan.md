# Resume Analyser & Ranker — Django Project Specification

> For use with AI Agent (Claude Opus)

---

## 1. Overview

A two-role HR platform where candidates register, browse vacancies, and submit resumes. HR admins manage vacancies and view AI-powered ranked applicants with detailed analysis. Resume analysis runs asynchronously via Celery + Redis using a local Ollama model. The project includes a full Django-templated UI styled with Tailwind CSS.

---

## 2. Roles

| Role | Capabilities |
|---|---|
| **Candidate** | Register, login, browse vacancies, submit resume + personal details, view own application status only |
| **HR Admin** | Login, full CRUD on vacancies, view ranked applicants per vacancy, view full analytics per applicant, view uploaded PDF |

---

## 3. Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 4.2+ |
| API | Django REST Framework |
| Auth | JWT via `djangorestframework-simplejwt` |
| Task Queue | Celery 5.3+ |
| Broker / Backend | Redis |
| PDF Text Extraction | PyMuPDF (`fitz`) |
| AI Inference | Ollama Python client — model: `qwen3.5:4b` |
| Database | PostgreSQL |
| Env Vars | `django-environ` |
| CORS | `django-cors-headers` |
| Templating | Django Templates |
| Styling | Tailwind CSS (CDN) |
| JS | Vanilla JS / Fetch API |
| Charts | Chart.js (CDN) |
| PDF Viewer | Browser native (`<iframe>` / `window.open`) |

---

## 4. Project Structure

4 Django apps — no notifications app.

| App | Responsibility |
|---|---|
| `users` | Custom user model, registration, JWT login |
| `vacancies` | HR CRUD on job postings |
| `applications` | Candidate submission + file upload + Celery task trigger |
| `analytics` | Stores AI analysis results, powers HR ranking view |

### Directory Layout

```
resumeanalyser/
├── manage.py
├── requirements.txt
├── .env.example
├── resumeanalyser/               ← project config
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
├── users/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── permissions.py
├── vacancies/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── applications/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── tasks.py                  ← Celery task lives here
├── analytics/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
└── templates/
    ├── base.html
    ├── auth/
    │   ├── login.html
    │   └── register.html
    ├── candidate/
    │   ├── vacancy_list.html
    │   ├── vacancy_detail.html
    │   └── my_applications.html
    └── hr/
        ├── dashboard.html
        ├── vacancy_list.html
        ├── vacancy_form.html
        ├── applicants_list.html
        └── applicant_detail.html
```

---

## 5. Database Schema

All primary keys use `UUIDField`. FK typo in original JSON (`Users(UserID)`) corrected to `Users(ID)`.

### 5.1 Users

| Column | Type | Constraints |
|---|---|---|
| ID | UUIDField | PRIMARY KEY |
| Username | VARCHAR(255) | NOT NULL |
| Email | VARCHAR(255) | NOT NULL, UNIQUE |
| PhoneNumber | VARCHAR(255) | NOT NULL |
| Password | VARCHAR(255) | NOT NULL (hashed) |
| Role | VARCHAR(255) | NOT NULL — `'candidate'` or `'hr'` |

### 5.2 Vacancies

| Column | Type | Constraints |
|---|---|---|
| ID | UUIDField | PRIMARY KEY |
| AdminID | FK → Users(ID) | NOT NULL |
| Title | VARCHAR(255) | NOT NULL |
| Description | TEXT | NOT NULL |
| Requirements | TEXT | NOT NULL |
| NoOfPositions | IntegerField | NOT NULL ← added per spec |
| Date | DateField | NOT NULL ← added per spec |
| CreatedAt | Timestamp | NOT NULL, auto |

### 5.3 Applications

| Column | Type | Constraints |
|---|---|---|
| ID | UUIDField | PRIMARY KEY |
| VacancyID | FK → Vacancies(ID) | NOT NULL |
| UserID | FK → Users(ID) | NOT NULL |
| AppliedAt | Timestamp | NOT NULL, auto |
| Status | VARCHAR(255) | NOT NULL — `pending` / `processing` / `analysed` / `rejected` |
| DocumentReference | TEXT | NOT NULL — relative path to PDF in `media/resumes/` |

### 5.4 Analytics

| Column | Type | Constraints |
|---|---|---|
| ID | UUIDField | PRIMARY KEY |
| ApplicationID | FK → Applications(ID) | NOT NULL |
| VacancyID | VARCHAR(255) | NOT NULL |
| OverallScore | INT | NOT NULL |
| Rating | VARCHAR(50) | NOT NULL |
| Strengths | JSON | NOT NULL |
| AreasToImprove | JSON | NOT NULL |
| SectionBreakdownPercentage | JSON | NOT NULL |
| KeywordAnalysis | JSON | NOT NULL |
| Projects | JSON | NOT NULL ← added per spec |
| Experience | JSON | NOT NULL ← added per spec |
| FinalSummary | TEXT | NOT NULL |
| CreatedAt | TIMESTAMP | NOT NULL, auto |

---

## 6. API Endpoints

### Auth

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/api/auth/register/` | Public | Register new user |
| POST | `/api/auth/login/` | Public | Returns JWT access + refresh tokens |
| POST | `/api/auth/refresh/` | Public | Refresh access token |

### Users

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/api/users/me/` | Authenticated | Get own profile |
| PATCH | `/api/users/me/` | Authenticated | Update own profile |

### Vacancies

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/api/vacancies/` | Public | List all vacancies |
| POST | `/api/vacancies/` | HR only | Create vacancy |
| GET | `/api/vacancies/{id}/` | Public | Retrieve vacancy detail |
| PUT / PATCH | `/api/vacancies/{id}/` | HR only | Update vacancy |
| DELETE | `/api/vacancies/{id}/` | HR only | Delete vacancy |
| GET | `/api/vacancies/{id}/applicants/` | HR only | Ranked applicants — sorted by `OverallScore DESC` |

### Applications

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/api/applications/` | Candidate only | Submit — multipart: `vacancy_id` + resume PDF |
| GET | `/api/applications/` | Candidate (own) / HR (all) | List applications |
| GET | `/api/applications/{id}/` | Owner / HR | Detail — status only for candidate |
| PATCH | `/api/applications/{id}/status/` | HR only | Update application status |

### Analytics

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/api/analytics/{application_id}/` | HR only | Full analysis detail — candidates cannot access |

---

## 7. Permissions

| Action | Candidate | HR |
|---|---|---|
| Register / Login | ✅ | ✅ |
| Browse vacancies | ✅ | ✅ |
| Create / Edit / Delete vacancy | ❌ | ✅ |
| Submit application + PDF | ✅ | ❌ |
| View own application status | ✅ | — |
| View all applications | ❌ | ✅ |
| View analytics / scores / ranking | ❌ | ✅ |
| View uploaded PDF | ❌ | ✅ |

---

## 8. Celery Task Flow

File: `applications/tasks.py`

```
Candidate POSTs multipart form (vacancy_id + resume PDF)
        ↓
Server saves Application row — Status: 'pending'
PDF saved to media/resumes/<uuid>.pdf
        ↓
Celery task fired → analyse_resume.delay(application_id)
        ↓
Task sets Application.Status → 'processing'
        ↓
Task fetches Application + linked Vacancy from DB
        ↓
PyMuPDF opens PDF from disk → extracts raw text
        ↓
Ollama AI called:
    job_pos     = Vacancy.Title
    pref_quali  = Vacancy.Requirements
    resume_text = extracted PDF text
    model       = qwen3.5:4b
        ↓
JSON response parsed from response['message']['content']
        ↓
Analytics row created with all fields
        ↓
Application.Status → 'analysed'
```

---

## 9. AI Analyser Details

| Parameter | Source |
|---|---|
| `job_pos` | `Vacancy.Title` |
| `pref_quali` | `Vacancy.Requirements` |
| `resume_text` | Extracted from uploaded PDF via PyMuPDF |

### AI JSON Response Field Mapping

| JSON Field | Maps to Analytics Column | Note |
|---|---|---|
| `overall_score` | OverallScore | |
| `rating` | Rating | |
| `strengths` | Strengths | JSON array |
| `areas_to_improve` | AreasToImprove | JSON array |
| `section_breakdown_percentage` | SectionBreakdownPercentage | JSON object |
| `keyword_analysis` | KeywordAnalysis | JSON object |
| `projects` | Projects | JSON array — new column |
| `experience` | Experience | JSON array — new column |
| `final_summary` | FinalSummary | |
| `name`, `email`, `ph_number` | **IGNORED** | Already stored in Users table |

---

## 10. UI Pages

### Public Pages

| Page | Route | Description |
|---|---|---|
| Landing / Login | `/` | Login form, link to register |
| Register | `/register/` | Name, email, phone, password, role select |

### Candidate Pages

| Page | Route | Description |
|---|---|---|
| Vacancy List | `/vacancies/` | Cards of open vacancies with title, date, positions |
| Vacancy Detail | `/vacancies/{id}/` | Full description + Apply button + resume upload form |
| My Applications | `/my-applications/` | List of own submissions with colour-coded status badge |

### HR Pages

| Page | Route | Description |
|---|---|---|
| HR Dashboard | `/hr/dashboard/` | Summary cards — total vacancies, total applicants, pending analyses |
| Vacancy Manager | `/hr/vacancies/` | Table with Create / Edit / Delete actions |
| Create Vacancy | `/hr/vacancies/create/` | Form — title, desc, requirements, positions, date |
| Edit Vacancy | `/hr/vacancies/{id}/edit/` | Same form pre-populated |
| Vacancy Applicants | `/hr/vacancies/{id}/applicants/` | Ranked list sorted by score with rating badge |
| Applicant Detail | `/hr/applications/{id}/` | Full analytics — score, strengths, weaknesses, keyword analysis, section bar chart + View PDF button |

### Template Structure

```
templates/
├── base.html                      ← navbar, auth state, Tailwind CDN, Chart.js CDN
├── auth/
│   ├── login.html
│   └── register.html
├── candidate/
│   ├── vacancy_list.html
│   ├── vacancy_detail.html
│   └── my_applications.html
└── hr/
    ├── dashboard.html
    ├── vacancy_list.html
    ├── vacancy_form.html
    ├── applicants_list.html
    └── applicant_detail.html      ← most complex — has score chart
```

### UI Notes

- `applicant_detail.html` renders `SectionBreakdownPercentage` JSON as a **visual bar chart** using Chart.js
- Status badges are colour-coded: `pending` = yellow, `processing` = blue, `analysed` = green, `rejected` = red
- HR pages are protected at both view level (Django login + role check) and template level
- Resume upload uses `multipart/form-data` — JS shows a loading spinner while Celery processes
- Candidates cannot navigate to any `/hr/` route

---

## 11. Requirements.txt

```
Django>=4.2,<5.0
djangorestframework>=3.15
djangorestframework-simplejwt>=5.3
celery>=5.3
redis>=5.0
django-environ>=0.11
psycopg2-binary>=2.9
pymupdf>=1.24
ollama
django-cors-headers>=4.3
```

---

## 12. Environment Variables (.env)

```
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=resumeanalyser
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
MEDIA_URL=/media/
MEDIA_ROOT=media/
```

---

## 13. Key Implementation Notes

- Custom User model extends `AbstractBaseUser` — set `AUTH_USER_MODEL = 'users.User'` in `settings.py`
- All PKs use `UUIDField(default=uuid.uuid4, editable=False)`
- PDF files saved to `media/resumes/<uuid>.pdf`; `DocumentReference` stores the relative path
- `tasks.py` has a clearly marked plug-in point where the Ollama client call lives
- `name`, `email`, `ph_number` from AI response are ignored — candidate data already in Users table
- `GET /api/vacancies/{id}/applicants/` joins Applications → Analytics, ordered by `OverallScore DESC`
- Candidate serializer for `/api/applications/{id}/` returns **only** `id`, `vacancy`, `status`, `applied_at`
- Candidates have zero access to analytics endpoints — permission denied at view level
- `AUTH_USER_MODEL` must be set before the first migration

---

## 14. Code Generation Order

| Step | File | Notes |
|---|---|---|
| 1 | `requirements.txt` + `.env.example` | |
| 2 | `resumeanalyser/settings.py` | DB, JWT, Celery, DRF, media, templates config |
| 3 | `resumeanalyser/celery.py` | Celery app init |
| 4 | `resumeanalyser/urls.py` | Root URL conf — API + template routes |
| 5 | `users/models.py` | Must come first — other apps FK to this |
| 6 | `users/permissions.py` | `IsHR` custom permission class |
| 7 | `users/serializers.py` + `views.py` + `urls.py` | |
| 8 | `vacancies/models.py` + `serializers.py` + `views.py` + `urls.py` | |
| 9 | `applications/models.py` + `serializers.py` + `views.py` + `urls.py` | |
| 10 | `applications/tasks.py` | Celery task — AI analyser plug-in point |
| 11 | `analytics/models.py` + `serializers.py` + `views.py` + `urls.py` | |
| 12 | `templates/base.html` | Navbar, Tailwind CDN, Chart.js CDN |
| 13 | `templates/auth/login.html` + `register.html` | |
| 14 | `templates/candidate/vacancy_list.html` | |
| 15 | `templates/candidate/vacancy_detail.html` + `my_applications.html` | |
| 16 | `templates/hr/dashboard.html` | |
| 17 | `templates/hr/vacancy_list.html` + `vacancy_form.html` | |
| 18 | `templates/hr/applicants_list.html` | |
| 19 | `templates/hr/applicant_detail.html` | Most complex — score chart, full analytics |
