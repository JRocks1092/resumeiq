"""
Celery task for resume–vacancy matching.

Queues the AI matching job so multiple candidates can submit simultaneously.
Results are stored in Redis via Celery's result backend (TTL set by
CELERY_RESULT_EXPIRES in settings.py).
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def match_resume(self, resume_text: str, vacancies: list) -> list:
    """
    Async Celery task: match a candidate's resume against all available vacancies.

    Args:
        resume_text: Plain text extracted from the candidate's PDF resume.
        vacancies: List of vacancy dicts (id, title, description, requirements,
                   no_of_positions, date, created_at).

    Returns:
        List of vacancy dicts sorted by match_score descending, each with
        match_score and match_summary fields added.
    """
    from vacancies.match_utils import build_match_prompt, call_ollama, parse_match_response

    try:
        logger.info(f"Starting resume match task {self.request.id} against {len(vacancies)} vacancies")

        # 1. Build prompt
        prompt = build_match_prompt(vacancies, resume_text)

        # 2. Call Ollama
        raw_response = call_ollama(prompt)

        # 3. Parse + validate response
        results = parse_match_response(raw_response)

        logger.info(f"Match task {self.request.id} completed successfully — {len(results)} results")
        return results

    except Exception as exc:
        logger.error(f"Error in match task {self.request.id}: {exc}")
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for match task {self.request.id}")
            raise
