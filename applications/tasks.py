"""
Celery task for AI-powered resume analysis.

Flow:
1. Receives application_id
2. Sets status to 'processing'
3. Extracts text from PDF using PyMuPDF
4. Sends to Ollama AI for analysis
5. Parses JSON response
6. Creates Analytics record
7. Sets status to 'analysed'
"""

import json
import logging
import os
import re
from ollama import Client
import fitz  # PyMuPDF
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

# ─── AI Prompt Template ─────────────────────────────────────

ANALYSIS_PROMPT = """You are an expert HR resume analyst. Analyze the following resume against the job requirements.

**Job Position:** {job_pos}

**Preferred Qualifications:**
{pref_quali}

**Resume Text:**
{resume_text}

Respond with ONLY a valid JSON object (no markdown, no code blocks, no extra text). Use this exact structure:

{{
    "overall_score": <integer 0-100>,
    "rating": "<Excellent|Good|Average|Below Average|Poor>",
    "strengths": ["strength 1", "strength 2", "strength 3"],
    "areas_to_improve": ["area 1", "area 2", "area 3"],
    "section_breakdown_percentage": {{
        "education": <integer 0-100>,
        "experience": <integer 0-100>,
        "skills": <integer 0-100>,
        "projects": <integer 0-100>,
        "certifications": <integer 0-100>
    }},
    "keyword_analysis": {{
        "matched_keywords": ["keyword1", "keyword2"],
        "missing_keywords": ["keyword3", "keyword4"],
        "match_percentage": <integer 0-100>
    }},
    "projects": [
        {{
            "name": "project name",
            "description": "brief description",
            "relevance": "<High|Medium|Low>"
        }}
    ],
    "experience": [
        {{
            "role": "job title",
            "company": "company name",
            "duration": "time period",
            "relevance": "<High|Medium|Low>"
        }}
    ],
    "final_summary": "A comprehensive 2-3 sentence summary of the candidate's fit for this role."
}}
"""


def extract_text_from_pdf(pdf_path):
    """Extract all text from a PDF file using PyMuPDF."""
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
        raise
    return text.strip()


def parse_ai_response(content):
    """
    Parse the AI response to extract JSON.
    Handles cases where the model wraps JSON in markdown code blocks.
    """
    # Try direct JSON parse first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding JSON object pattern
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse AI response as JSON: {content[:500]}")


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def analyse_resume(self, application_id):
    """
    Async Celery task to analyse a resume using Ollama AI.

    Args:
        application_id: UUID string of the Application to analyse.
    """
    from applications.models import Application
    from analytics.models import Analytics

    try:
        # Fetch application + linked vacancy
        application = Application.objects.select_related('vacancy').get(id=application_id)

        # Set status to processing
        application.status = 'processing'
        application.save(update_fields=['status'])

        logger.info(f"Processing application {application_id} for vacancy '{application.vacancy.title}'")

        # Extract text from PDF
        pdf_path = os.path.join(settings.MEDIA_ROOT, application.document_reference)
        resume_text = extract_text_from_pdf(pdf_path)

        if not resume_text:
            raise ValueError("No text could be extracted from the PDF.")

        # Prepare prompt
        prompt = ANALYSIS_PROMPT.format(
            job_pos=application.vacancy.title,
            pref_quali=application.vacancy.requirements,
            resume_text=resume_text[:8000],  # Limit text length for model context
        )

        # ─── OLLAMA AI CALL — plug-in point ─────────────────


        client = Client(
            host=settings.OLLAMA_URL,
            timeout=300.0
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
                'num_predict': 2048,
            },
            think=settings.OLLAMA_THINK
        )
        # ─────────────────────────────────────────────────────

        # Parse the AI response
        ai_content = response['message']['content']
        analysis = parse_ai_response(ai_content)

        # Create Analytics record
        Analytics.objects.create(
            application=application,
            vacancy_id=str(application.vacancy.id),
            overall_score=analysis.get('overall_score', 0),
            rating=analysis.get('rating', 'N/A'),
            strengths=analysis.get('strengths', []),
            areas_to_improve=analysis.get('areas_to_improve', []),
            section_breakdown_percentage=analysis.get('section_breakdown_percentage', {}),
            keyword_analysis=analysis.get('keyword_analysis', {}),
            projects=analysis.get('projects', []),
            experience=analysis.get('experience', []),
            final_summary=analysis.get('final_summary', ''),
        )

        # Update status to analysed
        application.status = 'analysed'
        application.save(update_fields=['status'])

        logger.info(f"Successfully analysed application {application_id}")
        return {'status': 'success', 'application_id': application_id}

    except Application.DoesNotExist:
        logger.error(f"Application {application_id} not found.")
        return {'status': 'error', 'message': 'Application not found'}

    except Exception as exc:
        logger.error(f"Error analysing application {application_id}: {exc}")
        # Retry on transient errors
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            # Mark as pending so it can be retried later
            try:
                application = Application.objects.get(id=application_id)
                application.status = 'pending'
                application.save(update_fields=['status'])
            except Application.DoesNotExist:
                pass
            logger.error(f"Max retries exceeded for application {application_id}")
            return {'status': 'error', 'message': str(exc)}
