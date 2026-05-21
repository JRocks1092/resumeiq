"""
Utility functions for resume–vacancy matching.

Handles:
- In-memory PDF text extraction (never saved to disk)
- AI prompt construction
- Ollama API call
- Response parsing and validation
"""

import json
import logging
import re

import fitz  # PyMuPDF
from ollama import Client
from django.conf import settings

logger = logging.getLogger(__name__)

# ─── AI Prompt Template ─────────────────────────────────────

MATCH_PROMPT = """You are a recruitment assistant that evaluates resumes against job openings.

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

JOBS: {jobs_json}
RESUME: {resume_text}"""


# ─── Step 1: Extract text from uploaded PDF bytes (in memory) ─

def extract_pdf_text(pdf_bytes: bytes) -> str:
    """
    Extract all plain text from a PDF file loaded in memory.
    Never writes to disk.
    """
    text = ""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        logger.error(f"Error extracting text from in-memory PDF: {e}")
        raise
    return text.strip()


# ─── Step 2: Build prompt ─────────────────────────────────────

def build_match_prompt(jobs: list, resume_text: str) -> str:
    """
    Build the full prompt string by injecting the jobs JSON array
    and the resume plain text into the prompt template.
    """
    jobs_json = json.dumps(jobs, default=str)
    return MATCH_PROMPT.format(
        jobs_json=jobs_json,
        resume_text=resume_text[:8000],  # Limit text length for model context
    )


# ─── Step 3: Call Ollama ──────────────────────────────────────

def call_ollama(prompt: str) -> str:
    """
    Send the prompt to Ollama and return the raw response content string.
    """
    client = Client(
        host=settings.OLLAMA_URL,
        timeout=300.0,
    )

    response = client.chat(
        model=settings.OLLAMA_MODEL,
        messages=[
            {
                'role': 'user',
                'content': prompt,
            }
        ],
        options={
            'temperature': 0.3,
            'num_predict': 4096,
        },
        think=False,  # Always disable thinking for match — we want pure JSON
    )

    return response['message']['content']


# ─── Step 4: Parse & validate response ────────────────────────

def parse_match_response(raw: str) -> list:
    """
    Parse the raw Ollama response into a validated list of vacancy dicts
    with match_score and match_summary fields added.

    Tries:
    1. Direct JSON parse
    2. Extract JSON array from markdown code block
    3. Extract first [...] pattern
    """
    parsed = None

    # Attempt 1: direct JSON parse
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Attempt 2: extract from markdown code block
    if parsed is None:
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

    # Attempt 3: find raw JSON array pattern
    if parsed is None:
        json_match = re.search(r'\[.*\]', raw, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

    if parsed is None:
        raise ValueError(f"Could not parse match response as JSON: {raw[:500]}")

    # If we got a dict with a list inside, unwrap it
    if isinstance(parsed, dict):
        for key in parsed:
            if isinstance(parsed[key], list):
                parsed = parsed[key]
                break
        else:
            raise ValueError("Parsed JSON is a dict but contains no list of results.")

    if not isinstance(parsed, list):
        raise ValueError(f"Expected a JSON array, got {type(parsed).__name__}")

    # Validate and clean each item
    cleaned = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        # Ensure match_score exists and is numeric
        score = item.get('match_score', 0)
        try:
            score = int(float(score))
        except (TypeError, ValueError):
            score = 0
        item['match_score'] = max(0, min(100, score))

        # Ensure match_summary exists
        if 'match_summary' not in item or not item['match_summary']:
            item['match_summary'] = 'No summary available.'

        cleaned.append(item)

    # Sort by match_score descending
    cleaned.sort(key=lambda x: x['match_score'], reverse=True)

    return cleaned
