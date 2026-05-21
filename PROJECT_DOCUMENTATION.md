# Resume Analyser Django Project Documentation

## 1. Project Overview

This Django project is a resume analysis and ranking platform with two primary user roles:
- **Candidates**: register, login, browse vacancies, upload resume PDFs, and view their submitted applications.
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
├── vacancies/              # Vacancy CRUD and vacancy pages
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

Key behavior:
- `Vacancy` model stores job postings with fields like `title`, `description`, `requirements`, `no_of_positions`, and `date`.
- `VacancySerializer` includes `admin_name` via the foreign key to the user who created the vacancy.
- Vacancy list is public; creation, update, and deletion are restricted to HR users via `IsHR`.
- Template pages include candidate vacancy browsing and HR vacancy management.

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

---

## 5. AI Resume Analysis Flow

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
