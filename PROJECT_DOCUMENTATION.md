# Resume Analyser Django Project Documentation

## 1. Project Overview

This Django project is a resume analysis and ranking platform with two primary user roles:
- **Candidates**: register, login, browse vacancies, upload resume PDFs, view submitted applications, and **match their resume against all open vacancies** to see a ranked fit score.
- **HR Admins**: create and manage vacancies, view candidate applications, and see AI-generated resume analysis with ranking.

The project uses Django, Django REST Framework, Celery, local Ollama AI, SQLite (for local development), and Django Templates.

---

## 2. Root Structure

```
resume_final/
├── manage.py
├── requirements.txt
├── db.sqlite3
├── memory.md
├── resume_analyser_plan.md
├── resumeanalyser/          # Django project configuration
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   ├── asgi.py
│   └── wsgi.py
├── users/                   # Custom user management + auth
├── vacancies/              # Vacancy CRUD, vacancy pages, and resume–vacancy matching
├── applications/           # Candidate application upload + resume ingestion
├── analytics/              # AI analysis storage + ranked applicant views
├── templates/              # HTML pages for candidate and HR UIs
└── static/                 # Static assets folder
```

---

## 3. Core Django Settings

File: `resumeanalyser/settings.py`

Key configuration:
- `AUTH_USER_MODEL = 'users.User'` — custom UUID-based user model.
- `DATABASES` uses SQLite locally (`db.sqlite3`).
- `REST_FRAMEWORK` sets JWT authentication via `rest_framework_simplejwt`.
- `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` use Redis by default.
- `MEDIA_ROOT` and `MEDIA_URL` are configured for resume uploads.
- `OLLAMA_MODEL`, `OLLAMA_URL`, and `OLLAMA_THINK` define the local Ollama inference model settings.

Installed apps include:
- Django core: admin, auth, sessions, etc.
- Third-party: `rest_framework`, `rest_framework_simplejwt`, `corsheaders`.
- Local apps: `users`, `vacancies`, `applications`, `analytics`.

The `resumeanalyser/urls.py` file routes:
- API paths under `/api/`
- HTML template page views at root-level paths
- Static media serving in debug mode

---

## 4. App Responsibilities and Code Flow

### 4.1 `users/`

Main files:
- `models.py`
- `serializers.py`
- `views.py`
- `permissions.py`

Key behavior:
- `User` custom model uses `UUIDField` for `id` and stores `username`, `email`, `phone_number`, and `role`.
- Two roles are supported: `candidate` and `hr`.
- `UserManager` implements `create_user` and `create_superuser`.
- `RegisterSerializer` creates users with hashed passwords.
- `UserProfileView` returns and updates the authenticated user's profile.
- `LoginPageView` and `RegisterPageView` serve HTML pages for auth.
- `IsHR` and `IsCandidate` permissions gate HR and candidate-only API actions.

### 4.2 `vacancies/`

Main files:
- `models.py`
- `serializers.py`
- `views.py`
- `match_utils.py` — utility functions for resume–vacancy matching
- `match_tasks.py` — Celery task for async matching

Key behavior:
- `Vacancy` model stores job postings with fields like `title`, `description`, `requirements`, `no_of_positions`, and `date`.
- `VacancySerializer` includes `admin_name` via the foreign key to the user who created the vacancy.
- Vacancy list is public; creation, update, and deletion are restricted to HR users via `IsHR`.
- Template pages include candidate vacancy browsing and HR vacancy management.
- **Resume–Vacancy Matching** (candidate-only) is documented in section 4.5 below.

### 4.3 `applications/`

Main files:
- `models.py`
- `serializers.py`
- `views.py`
- `tasks.py`

Key behavior:
- `Application` model tracks a candidate's submission with a UUID key, `vacancy` relationship, `user`, `status`, and `document_reference` for the uploaded PDF.
- Allowed statuses: `pending`, `processing`, `analysed`, `rejected`.
- `ApplicationCreateSerializer` handles multipart form upload of `vacancy_id` and resume PDF.
- The resume is saved under `media/resumes/` with a generated UUID filename.
- Duplicate applications are blocked by checking `vacancy_id` + `user`.
- On successful submission, the app triggers the Celery task `analyse_resume.delay(str(application.id))`.
- Candidates can list only their own applications; HR users can list all applications.
- Application detail view restricts candidates from viewing other users' applications.

### 4.4 `analytics/`

Main files:
- `models.py`
- `serializers.py`
- `views.py`

Key behavior:
- `Analytics` model stores AI analysis results linked one-to-one with an `Application`.
- It contains:
  - `overall_score`
  - `rating`
  - `strengths`
  - `areas_to_improve`
  - `section_breakdown_percentage`
  - `keyword_analysis`
  - `projects`
  - `experience`
  - `final_summary`
- HR-only API endpoints expose full analytics details and ranked applicant lists.
- The vacancy applicants endpoint sorts analysed candidates by `overall_score`, with unanalysed candidates appended afterward.
- Template pages include HR dashboard, applicant list, and applicant detail.

### 4.5 Resume–Vacancy Matching (`vacancies/match_*`)

This feature allows candidates to upload their resume PDF and see **all open vacancies ranked by fit**, with a match score (0–100) and a plain-English summary per vacancy. It is a discovery/exploration tool — it does **not** create an Application record.

**Architecture:**
- Processing runs via **Celery** (because Ollama handles one request at a time).
- Results are stored temporarily in **Redis** with a 10-minute TTL (`CELERY_RESULT_EXPIRES = 600`). No database writes.
- The frontend polls for completion and renders results when ready.

**Files:**

| File | Purpose |
|---|---|
| `vacancies/match_utils.py` | In-memory PDF text extraction (`fitz`), prompt builder, Ollama API call, JSON response parser |
| `vacancies/match_tasks.py` | Celery task `match_resume` — orchestrates the matching pipeline with 3 retries |
| `vacancies/views.py` | `VacancyMatchSubmitView` (POST) and `VacancyMatchResultView` (GET) API views, plus `MatchPageView` template view |
| `templates/candidate/match.html` | Full UI with 4 states: idle (upload form), loading (spinner + progress bar), success (ranked cards), error |

**Flow:**
1. Candidate uploads a resume PDF on `/match/`.
2. `POST /api/vacancies/match/` validates the PDF (type, size ≤ 5MB), extracts text in memory (never saved to disk), fetches all vacancies where `date >= today`, and queues `match_resume.delay()`.
3. Server returns `{ "task_id": "..." }` with HTTP 202.
4. Frontend polls `GET /api/vacancies/match/{task_id}/` every 3 seconds (timeout: 3 minutes).
5. Celery worker builds a single prompt with ALL jobs + resume, calls Ollama once, parses the JSON response, sorts by `match_score` descending, and stores results in Redis.
6. Poll returns `{ "status": "SUCCESS", "results": [...] }` — frontend renders ranked vacancy cards with color-coded score bars (green ≥80, yellow ≥50, red <50).

**Permissions:** Both endpoints require `IsAuthenticated` + `IsCandidate`. HR users cannot access this feature.

---

## 5. AI Flows

### 5.1 Resume Analysis (per-application)

File: `applications/tasks.py`

This is the core asynchronous analysis flow:
1. Candidate submits a resume PDF through `/api/applications/`.
2. `ApplicationCreateView` creates the application record and queues `analyse_resume`.
3. `analyse_resume`:
   - loads the application and marks it `processing`
   - extracts text from the PDF using `fitz` from PyMuPDF
   - builds a prompt including vacancy title, requirements, and resume text
   - calls the Ollama client using `settings.OLLAMA_URL` and `settings.OLLAMA_MODEL`
   - parses the model response into JSON
   - creates an `Analytics` record from the parsed output
   - updates the application status to `analysed`

Important implementation details:
- The task uses `@shared_task(bind=True, max_retries=3, default_retry_delay=30)`.
- `parse_ai_response` attempts direct JSON parsing, code block extraction, and fallback regex extraction.
- If the task ultimately fails after retries, it sets the application back to `pending`.

### 5.2 Resume–Vacancy Matching (candidate exploration)

Files: `vacancies/match_utils.py`, `vacancies/match_tasks.py`

This flow lets candidates match their resume against **all open vacancies at once** without creating an application:
1. PDF text is extracted **in memory** (never saved to disk) via `extract_pdf_text(pdf_bytes)`.
2. All vacancies with `date >= today` are serialized to a JSON array.
3. `build_match_prompt()` inserts the jobs JSON and resume text into the AI prompt template.
4. `call_ollama()` sends a single prompt to the Ollama model (with `think=False` forced).
5. `parse_match_response()` parses the JSON array response, validates `match_score` (0–100) and `match_summary` per vacancy, and sorts by score descending.
6. Results are returned to Celery's result backend (Redis) with a 10-minute TTL.

The Celery task `match_resume` uses `@shared_task(bind=True, max_retries=3, default_retry_delay=30)` — same retry strategy as `analyse_resume`.

---

## 6. URL and Page Routing

### API endpoints

Auth:
- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`

User profile:
- `GET /api/users/me/`
- `PATCH /api/users/me/`

Vacancies:
- `GET /api/vacancies/`
- `POST /api/vacancies/`
- `GET /api/vacancies/available/`
- `GET /api/vacancies/{id}/`
- `PUT/PATCH /api/vacancies/{id}/`
- `DELETE /api/vacancies/{id}/`
- `GET /api/vacancies/{id}/applicants/`
- `POST /api/vacancies/match/` — upload resume PDF, returns `task_id` (HTTP 202) *(candidate only)*
- `GET /api/vacancies/match/{task_id}/` — poll match task status/results *(candidate only)*

Applications:
- `POST /api/applications/`
- `GET /api/applications/list/`
- `GET /api/applications/{id}/`
- `PATCH /api/applications/{id}/status/`

Analytics:
- `GET /api/analytics/{application_id}/`

### Template pages

Authentication:
- `/` — login page
- `/register/` — registration page

Candidate pages:
- `/vacancies/` — vacancy listing
- `/vacancies/{id}/` — vacancy detail
- `/match/` — resume–vacancy matching (upload + ranked results)
- `/my-applications/` — candidate applications list

HR pages:
- `/hr/dashboard/` — HR dashboard
- `/hr/vacancies/` — HR vacancy management list
- `/hr/vacancies/create/` — create vacancy
- `/hr/vacancies/{id}/edit/` — edit vacancy
- `/hr/vacancies/{id}/applicants/` — applicant ranking list
- `/hr/applications/{id}/` — applicant detail page

---

## 7. Key Code Concepts

### Custom user model
- `users/models.py` defines `User` with UUID primary key.
- Email is the login field (`USERNAME_FIELD = 'email'`).
- `is_hr` and `is_candidate` properties simplify role checks.

### Permission classes
- `users/permissions.py` defines `IsHR` and `IsCandidate` for route protection.
- Views mix `permissions.IsAuthenticated` with these custom permissions as needed.

### Serializer separation
- Vacancy, application, and analytics serializer classes separate summary/list views from detailed views.
- `ApplicationCreateSerializer` manually saves PDF files and enforces PDF-only upload validation.

### TemplateViews for SPA-like pages
- Template view classes in each app return static templates with minimal context.
- JavaScript on these front-end pages likely consumes the REST API to display data.

---

## 8. Running the Project

Suggested local commands:

```bash
python manage.py migrate
python manage.py runserver
```

For Celery worker:

```bash
celery -A resumeanalyser worker --loglevel=info
```

Environment variables are loaded from `.env` with `django-environ`.

---

## 9. Notes from Existing Project Files

- `memory.md` tracks build progress and confirms the project has been restored, migrated, and validated.
- `resume_analyser_plan.md` describes the project concept, roles, and architecture.
- `match_feature_plan.md` details the resume–vacancy matching feature design, including prompt template, concurrency model, view logic, frontend states, and result card UI specification.

These notes show the current project state and implementation goals.

---

## 10. Recommended Improvements

Optional enhancements if you continue development:
- add full front-end JavaScript API wrappers for the pages
- add unit tests for views, serializers, and Celery tasks
- add admin registration for models in `admin.py`
- store uploaded files with Django `FileField` and `MEDIA_ROOT` management instead of manual filesystem writing
- add explicit rate-limiting and file size handling on uploads
- improve AI prompt handling and model response validation
