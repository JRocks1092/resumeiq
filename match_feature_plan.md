# Resume vs Vacancies Matcher — Feature Update Plan

> Addendum to: `resume_analyser_plan.md`
> Feature: Candidate Resume–Vacancy Matching

---

## 1. Feature Overview

Candidates can upload their resume PDF and see **all available vacancies ranked by how well their resume matches**, with a match score (0–100) and a 2-line plain-English summary per vacancy. This is a one-shot comparison — it does **not** create an Application record. It is a discovery/exploration tool for candidates only.

Because multiple candidates may use this simultaneously and Ollama processes one request at a time, the task runs via **Celery**. The result is stored temporarily in **Redis** (with a TTL — no DB write). The frontend polls for completion and renders results when ready.

---

## 2. How It Works

```
Candidate uploads resume PDF on the Match page
        ↓
POST /api/vacancies/match/
Server validates PDF → extracts plain text via PyMuPDF (fitz) in memory
Server fetches all Vacancies where date >= today (deadline not passed)
Fields sent to Ollama per vacancy: id, title, description, requirements, no_of_positions, date, created_at
Celery task queued → match_resume.delay(resume_text, vacancies)
Server immediately returns { task_id: "abc123" } — HTTP 202
        ↓
Frontend begins polling every 3 seconds:
GET /api/vacancies/match/{task_id}/
        ↓
Celery worker (when free) picks up task:
    - Builds single prompt with ALL available JOBS + RESUME
    - Calls Ollama (qwen3.5:4b) — one API call for all vacancies
    - Parses JSON response
    - Sorts by match_score DESC
    - Stores result in Redis with 10-minute TTL
    - Marks task as SUCCESS
        ↓
Poll returns { status: "SUCCESS", results: [...] }
        ↓
Frontend stops polling → renders ranked vacancy cards
```

---

## 3. Concurrency Model

| Scenario | Behaviour |
|---|---|
| 1 user submits | Task queued instantly, processed immediately |
| 3 users submit simultaneously | All get a `task_id` in <1s. Tasks queue in Redis. Processed one at a time by Celery worker. Each user's frontend polls independently |
| User closes tab mid-wait | Task still completes in background. Result sits in Redis until TTL expires (10 min). No wasted DB writes |
| Ollama fails / times out | Task retries up to 3 times. Poll returns `{ status: "FAILURE", error: "..." }` |

---

## 4. AI Prompt

```
You are a recruitment assistant that evaluates resumes against job openings.

You will be given:
1. A JSON array of job listings (with fields: id, title, description,
   requirements, no_of_positions, date, created_at)
2. A plain-text resume

Your task:
- For each job listing, evaluate how well the resume matches the role.
- Return the SAME job listing JSON array, preserving every original field exactly.
- Add two new fields to each listing:
    - "match_score": a number from 0 to 100 indicating how well the resume
      fits this role
    - "match_summary": a 1–2 sentence plain-English summary explaining the
      fit or gap
- Sort the output array by match_score descending (best match first).

Return ONLY valid JSON. No markdown, no explanation, no preamble.

Input format:

JOBS: <jobs json array>
RESUME: <resume plain text>
```

---

## 5. What Changes in the Codebase

### 5.1 New API Endpoints

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/api/vacancies/match/` | Candidate only | Upload PDF → queues Celery task → returns `task_id` (HTTP 202) |
| GET | `/api/vacancies/match/{task_id}/` | Candidate only | Poll task status → returns status + results when done |

**POST response (202):**
```json
{ "task_id": "abc123-def456" }
```

**GET poll response — pending:**
```json
{ "status": "PENDING" }
```

**GET poll response — success:**
```json
{
  "status": "SUCCESS",
  "results": [ ...ranked vacancies with match_score and match_summary... ]
}
```

**GET poll response — failure:**
```json
{ "status": "FAILURE", "error": "Ollama inference failed after 3 retries." }
```

### 5.2 New Files

| File | Purpose |
|---|---|
| `vacancies/match_utils.py` | PDF text extraction + prompt builder + Ollama call + response parser |
| `vacancies/match_tasks.py` | Celery task `match_resume` |

### 5.3 Modified Files

| File | Change |
|---|---|
| `vacancies/views.py` | Add `VacancyMatchSubmitView` and `VacancyMatchResultView` |
| `vacancies/urls.py` | Register both new API routes |
| `resumeanalyser/urls.py` | Add template route `/match/` |
| `resumeanalyser/celery.py` | Auto-discover picks up `match_tasks.py` automatically — no change needed |
| `templates/base.html` | Add "Match My Resume" to candidate navbar |
| `templates/candidate/match.html` | New page — upload form + polling logic + ranked results |

### 5.4 No DB Changes
No new models or migrations. Results live in Redis only, with a 10-minute TTL.

---

## 6. `match_tasks.py` — Celery Task

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def match_resume(self, resume_text: str, vacancies: list) -> list:
    # 1. Build prompt via match_utils.build_match_prompt()
    # 2. Call Ollama via match_utils.call_ollama()
    # 3. Parse + validate response via match_utils.parse_match_response()
    # 4. Return sorted results list
    # On exception: self.retry(exc=exc)
    # Result auto-stored in Redis by Celery result backend (TTL via CELERY_RESULT_EXPIRES)
```

**Celery settings to add in `settings.py`:**
```python
CELERY_RESULT_EXPIRES = 600  # Redis TTL: 10 minutes
```

---

## 7. `match_utils.py` — Logic Breakdown

```python
# Step 1 — Extract text from uploaded PDF (in memory — never saved to disk)
def extract_pdf_text(pdf_bytes: bytes) -> str:
    # Open with fitz.open(stream=pdf_bytes, filetype="pdf")
    # Return concatenated plain text from all pages

# Step 2 — Build prompt
def build_match_prompt(jobs: list, resume_text: str) -> str:
    # Serialise jobs list to JSON string
    # Insert into prompt template
    # Return full prompt string

# Step 3 — Call Ollama
def call_ollama(prompt: str) -> str:
    # client.chat(model=settings.OLLAMA_MODEL, messages=[...], think=False)
    # Return raw response['message']['content'] string

# Step 4 — Parse & validate response
def parse_match_response(raw: str) -> list:
    # Attempt direct JSON parse
    # Fallback: extract JSON array from code block
    # Validate each item has match_score and match_summary
    # Return cleaned and sorted list
```

---

## 8. View Logic

### `VacancyMatchSubmitView` (POST)
```
1. Check user is authenticated + is candidate
2. Validate uploaded file exists and is PDF
3. Read PDF bytes in memory → extract text via match_utils.extract_pdf_text()
4. Fetch all Vacancy objects → serialise to list of dicts
   (id, title, description, requirements, no_of_positions, date, created_at)
5. Queue task → result = match_resume.delay(resume_text, vacancies)
6. Return Response({ "task_id": result.id }, status=202)
```

### `VacancyMatchResultView` (GET)
```
1. Check user is authenticated + is candidate
2. Fetch AsyncResult(task_id) from Celery/Redis
3. If PENDING or STARTED → return { "status": "PENDING" }
4. If SUCCESS → return { "status": "SUCCESS", "results": result.get() }
5. If FAILURE → return { "status": "FAILURE", "error": str(result.result) }
```

**Error handling:**
- No file uploaded → 400
- File is not a PDF (`content_type != 'application/pdf'`) → 400 `"Only PDF files are accepted."`
- File exceeds 5MB (`file.size > 5 * 1024 * 1024`) → 400 `"File size must be under 5MB."`
- PDF text extraction fails → 400
- Invalid task_id → 404
- Task FAILURE after retries → 503

---

## 9. Frontend Polling Logic (`match.html`)

```javascript
// On form submit:
async function submitResume(formData) {
    // 1. POST formData to /api/vacancies/match/
    // 2. Get task_id from response
    // 3. Show "Analysing your resume..." spinner
    // 4. Start polling every 3 seconds → GET /api/vacancies/match/{task_id}/
    // 5. If status === "PENDING" → keep polling
    // 6. If status === "SUCCESS" → stop polling, render results
    // 7. If status === "FAILURE" → stop polling, show error message
    // 8. Timeout after 3 minutes → show "Taking too long, please try again"
}
```

---

## 10. Result Card UI

Each vacancy rendered as a card showing:
- Vacancy title + date + number of positions
- **Match score** — colour-coded progress bar
  - 80–100 → green
  - 50–79 → yellow
  - 0–49 → red
- **Match summary** — 1–2 sentence plain text
- "View Vacancy" button → `/vacancies/{id}/`

---

## 11. Response Schema

Each item in the results array:

```json
{
  "id": "uuid",
  "title": "Backend Engineer",
  "description": "...",
  "requirements": "...",
  "no_of_positions": 3,
  "date": "2026-06-01",
  "created_at": "2026-05-01T10:00:00Z",
  "match_score": 87,
  "match_summary": "Strong Python and Django background aligns well with the role. Lacks cloud deployment experience mentioned in requirements."
}
```

---

## 12. Updated Navbar Links

### Candidate Navbar (`base.html`)
| Link | Route |
|---|---|
| Vacancies | `/vacancies/` |
| **Match My Resume** ← new | `/match/` |
| My Applications | `/my-applications/` |

---

## 13. Requirements.txt

No new packages needed. All already present:

```
celery>=5.3        ← already in use
redis>=5.0         ← already in use (result backend)
pymupdf>=1.24      ← already in use
ollama             ← already in use
```

Only one settings addition:
```python
CELERY_RESULT_EXPIRES = 600  # add to settings.py
```

---

## 14. Code Generation Order

| Step | File | Notes |
|---|---|---|
| 1 | `vacancies/match_utils.py` | PDF extraction + prompt builder + Ollama call + parser |
| 2 | `vacancies/match_tasks.py` | Celery task `match_resume` |
| 3 | `vacancies/views.py` | Add `VacancyMatchSubmitView` + `VacancyMatchResultView` |
| 4 | `vacancies/urls.py` | Register both new API routes |
| 5 | `resumeanalyser/urls.py` | Add `/match/` template route |
| 6 | `resumeanalyser/settings.py` | Add `CELERY_RESULT_EXPIRES = 600` |
| 7 | `templates/base.html` | Add "Match My Resume" to candidate navbar |
| 8 | `templates/candidate/match.html` | Upload form + polling JS + ranked result cards |

---

## 16. Template Specification

### 16.1 Page: `templates/candidate/match.html`

Extends `base.html`. Candidate-only — redirect to login if unauthenticated.

---

### 16.2 Page States

The page has four distinct visual states managed by vanilla JS:

| State | When | What Shows |
|---|---|---|
| **Idle** | Page first loads | Upload form only |
| **Loading** | After submit, while polling | Spinner + status message + progress indicator |
| **Success** | Poll returns SUCCESS | Ranked vacancy cards |
| **Error** | Poll returns FAILURE or timeout | Error message + retry button |

---

### 16.3 Idle State — Upload Form

```
┌─────────────────────────────────────────────────┐
│                                                 │
│         Match Your Resume to Vacancies          │
│   Upload your resume and we'll rank all open    │
│   positions by how well you fit each role.      │
│                                                 │
│   ┌─────────────────────────────────────────┐   │
│   │                                         │   │
│   │        📄 Drop your PDF here            │   │
│   │        or click to browse               │   │
│   │                                         │   │
│   │        Accepts PDF only                 │   │
│   └─────────────────────────────────────────┘   │
│                                                 │
│   [ No file selected ]                          │
│                                                 │
│            [ Analyse My Resume ]                │
│                                                 │
└─────────────────────────────────────────────────┘
```

- Drag-and-drop zone with dashed border
- On file select: show filename + file size below the zone
- "Analyse My Resume" button disabled until a valid PDF is selected
- Client-side validation before any network request:
  - Reject non-PDF (`file.type !== 'application/pdf'`) → show `"Only PDF files are accepted."`
  - Reject files over 5MB (`file.size > 5 * 1024 * 1024`) → show `"File size must be under 5MB."`
  - Both checks show inline error under the upload zone and keep the button disabled

---

### 16.4 Loading State

Replaces the form area after submit. Form is hidden, not removed.

```
┌─────────────────────────────────────────────────┐
│                                                 │
│              Analysing your resume...           │
│                                                 │
│                  ⟳  (spinner)                   │
│                                                 │
│   Our AI is comparing your resume against       │
│   all open vacancies. This usually takes        │
│   15–30 seconds.                                │
│                                                 │
│   ░░░░░░░░░░░░░░░░░░░░  (animated progress bar) │
│                                                 │
│            [ Cancel ]                           │
│                                                 │
└─────────────────────────────────────────────────┘
```

- Animated spinning icon
- Indeterminate progress bar (CSS animation — not real progress)
- "Cancel" button stops polling and returns to idle state
- Polling interval: every 3 seconds via `setInterval`
- Timeout: after 3 minutes, stop polling and show error state

---

### 16.5 Success State — Ranked Results

Form hidden. Results rendered below a summary header.

```
┌─────────────────────────────────────────────────┐
│  ✓ Analysis complete — 6 vacancies matched      │
│                          [ Try Another Resume ] │
├─────────────────────────────────────────────────┤
│                                                 │
│  #1  Backend Engineer                    [ 92 ] │  ← green badge
│  ████████████████████░░  92%                    │  ← green bar
│  "Your Django and REST API experience is a      │
│   strong fit. Cloud deployment skills would     │
│   further strengthen your application."         │
│                              [ View Vacancy → ] │
├─────────────────────────────────────────────────┤
│  #2  Full Stack Developer                [ 74 ] │  ← yellow badge
│  ███████████████░░░░░░░  74%                    │  ← yellow bar
│  "Good frontend skills match the role but       │
│   limited DevOps experience is a gap."          │
│                              [ View Vacancy → ] │
├─────────────────────────────────────────────────┤
│  #3  Data Analyst                        [ 41 ] │  ← red badge
│  ████████░░░░░░░░░░░░░░  41%                    │  ← red bar
│  "Resume lacks statistical modelling and        │
│   SQL experience required for this role."       │
│                              [ View Vacancy → ] │
└─────────────────────────────────────────────────┘
```

**Score colour rules:**
- 80–100 → green (`bg-green-500`)
- 50–79 → yellow (`bg-yellow-400`)
- 0–49 → red (`bg-red-500`)

**Each card contains:**
- Rank number + vacancy title
- Score badge (right-aligned, colour-coded)
- Animated progress bar (width = match_score %)
- Match summary (2 lines max, plain text)
- "View Vacancy →" button → navigates to `/vacancies/{id}/`

**"Try Another Resume" button** — clears results, shows upload form again (resets to idle state)

---

### 16.6 Error State

```
┌─────────────────────────────────────────────────┐
│                                                 │
│   ✕  Something went wrong                      │
│                                                 │
│   We couldn't complete the analysis.            │
│   This is usually a temporary issue.            │
│                                                 │
│            [ Try Again ]                        │
│                                                 │
└─────────────────────────────────────────────────┘
```

Shown when:
- Task returns `FAILURE`
- Polling times out after 3 minutes
- Network error during polling

"Try Again" resets to idle state with form visible.

---

### 16.7 `base.html` Changes

One addition to the candidate navbar:

```html
<!-- existing -->
<a href="/vacancies/">Vacancies</a>
<a href="/my-applications/">My Applications</a>

<!-- new -->
<a href="/match/">Match My Resume</a>
```

No changes to the HR navbar — this link is candidate-only and conditionally rendered based on `user.role`.

---

### 16.8 JS State Machine (in `match.html`)

```
IDLE
  │
  │ user submits form
  ▼
LOADING ──── cancel button ──────────────────► IDLE
  │
  │ poll SUCCESS
  ▼
SUCCESS ──── "Try Another Resume" button ────► IDLE
  │
  │ poll FAILURE or timeout
  ▼
ERROR ──── "Try Again" button ───────────────► IDLE
```

All state transitions are handled by a single `setState(state)` JS function that shows/hides the correct section and starts/stops the polling interval.

---



- PDF validation enforced on **both** client and server — never trust client alone
- Accepted file type: PDF only (`content_type == 'application/pdf'`)
- Maximum file size: 5MB (`file.size <= 5 * 1024 * 1024`)
- Only vacancies where `date >= today` are included — expired vacancies are excluded
- Full `description` + `requirements` sent per vacancy for maximum matching accuracy
- PDF is processed **in memory only** — never saved to disk for this feature
- Results stored in **Redis only** with 10-minute TTL — no DB writes ever
- `IsCandidate` permission enforced on both endpoints — HR cannot access
- Reuses `settings.OLLAMA_MODEL` and `settings.OLLAMA_URL` from existing settings
- If vacancy count grows large (100+), consider trimming payload to `title` + `requirements` only to reduce Ollama token usage
- `task_id` is the Celery AsyncResult UUID — frontend stores it in JS memory for polling duration
