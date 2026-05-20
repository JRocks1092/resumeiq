# Resume Analyser & Ranker — Build Progress

> Tracking file for AI Agent build progress

---

## Current Focus
✅ **All code restored and verified.** DB switched to SQLite. Migrations applied. Ready to run!

---

## Build Steps

| Step | Description | Status | Notes |
|------|-------------|--------|-------|
| 1 | `requirements.txt` + `.env.example` | ✅ Done | |
| 2 | `resumeanalyser/settings.py` | ✅ Done | Switched to SQLite |
| 3 | `resumeanalyser/celery.py` | ✅ Done | |
| 4 | `resumeanalyser/urls.py` | ✅ Done | |
| 5 | `users/models.py` | ✅ Done | Custom User, UUID PK |
| 6 | `users/permissions.py` | ✅ Done | IsHR + IsCandidate |
| 7 | `users/serializers + views + urls` | ✅ Done | |
| 8 | `vacancies/*` | ✅ Done | |
| 9 | `applications/*` | ✅ Done | |
| 10 | `applications/tasks.py` | ✅ Done | Ollama client at 172.27.27.48:11434 |
| 11 | `analytics/*` | ✅ Done | |
| 12-19 | All templates | ✅ Done | |

---

## Validation Results
- ✅ `python manage.py check` — 0 issues
- ✅ `python manage.py makemigrations` — all migrations created
- ✅ `python manage.py migrate` — applied with SQLite
- ⬜ Manual testing

---

## Issue Log
- **Files wiped**: 27 Python files were found empty (cause unknown). All restored.
- **DB switch**: PostgreSQL → SQLite for simpler local dev
- **User changes**: Ollama model changed to `qwen3.5:9b`, client pointed to `172.27.27.48:11434`, `think=False` added

---

## To Run
```bash
# Start Django dev server
python manage.py runserver

# Start Celery worker (separate terminal)
celery -A resumeanalyser worker --loglevel=info
```
