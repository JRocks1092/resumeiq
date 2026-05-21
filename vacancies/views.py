"""
Views for the vacancies app — API + template views.
"""

import logging

from celery.result import AsyncResult
from django.utils.timezone import now
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from django.views.generic import TemplateView
from users.permissions import IsHR, IsCandidate
from .models import Vacancy
from .serializers import VacancySerializer, VacancyListSerializer, AvailableVacancyListSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .match_utils import extract_pdf_text
from .match_tasks import match_resume

logger = logging.getLogger(__name__)

# ─── API Views ───────────────────────────────────────────────

@api_view(['GET'])
def get_available_vacancies(request):
    """
    GET /api/vacancies/available/ — List all available vacancies
    """
    vacancies = Vacancy.objects.filter(date__gte=now().date())
    serializer = AvailableVacancyListSerializer(vacancies, many=True)
    return Response(serializer.data)


class VacancyListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/vacancies/       — List all vacancies (authenticated users)
    POST /api/vacancies/       — Create vacancy (HR only)
    """
    queryset = Vacancy.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return VacancySerializer
        return VacancyListSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), IsHR()]
        return [permissions.IsAuthenticated()]


class VacancyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/vacancies/{id}/  — Retrieve vacancy (authenticated users)
    PUT    /api/vacancies/{id}/  — Update vacancy (HR only)
    PATCH  /api/vacancies/{id}/  — Partial update (HR only)
    DELETE /api/vacancies/{id}/  — Delete vacancy (HR only)
    """
    queryset = Vacancy.objects.all()
    serializer_class = VacancySerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsHR()]


# ─── Match API Views ─────────────────────────────────────────

class VacancyMatchSubmitView(APIView):
    """
    POST /api/vacancies/match/
    Upload a PDF resume → queue a Celery matching task → return task_id (HTTP 202).
    Candidate-only endpoint.
    """
    permission_classes = [permissions.IsAuthenticated, IsCandidate]

    def post(self, request):
        # 1. Validate uploaded file exists
        pdf_file = request.FILES.get('resume')
        if not pdf_file:
            return Response(
                {'error': 'No file uploaded.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Validate file is a PDF
        if pdf_file.content_type != 'application/pdf':
            return Response(
                {'error': 'Only PDF files are accepted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Validate file size (max 5MB)
        if pdf_file.size > 5 * 1024 * 1024:
            return Response(
                {'error': 'File size must be under 5MB.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 4. Extract text from PDF in memory
        try:
            pdf_bytes = pdf_file.read()
            resume_text = extract_pdf_text(pdf_bytes)
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return Response(
                {'error': 'Failed to extract text from the PDF.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not resume_text:
            return Response(
                {'error': 'No text could be extracted from the PDF.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 5. Fetch all available vacancies (deadline not passed)
        vacancies = Vacancy.objects.filter(date__gte=now().date())
        if not vacancies.exists():
            return Response(
                {'error': 'No open vacancies available for matching.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vacancies_list = list(
            vacancies.values(
                'id', 'title', 'description', 'requirements',
                'no_of_positions', 'date', 'created_at',
            )
        )

        # Convert UUIDs and datetimes to strings for JSON serialization
        for v in vacancies_list:
            v['id'] = str(v['id'])
            v['date'] = str(v['date'])
            v['created_at'] = v['created_at'].isoformat() if v['created_at'] else None

        # 6. Queue Celery task
        result = match_resume.delay(resume_text, vacancies_list)

        return Response(
            {'task_id': result.id},
            status=status.HTTP_202_ACCEPTED,
        )


class VacancyMatchResultView(APIView):
    """
    GET /api/vacancies/match/{task_id}/
    Poll the Celery task status and return results when done.
    Candidate-only endpoint.
    """
    permission_classes = [permissions.IsAuthenticated, IsCandidate]

    def get(self, request, task_id):
        result = AsyncResult(task_id)

        if result.state in ('PENDING', 'STARTED', 'RETRY'):
            return Response({'status': 'PENDING'})

        if result.state == 'SUCCESS':
            return Response({
                'status': 'SUCCESS',
                'results': result.result,
            })

        if result.state == 'FAILURE':
            return Response(
                {
                    'status': 'FAILURE',
                    'error': str(result.result) if result.result else 'Ollama inference failed after 3 retries.',
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Catch-all for unexpected states
        return Response({'status': result.state})


# ─── Template Views ──────────────────────────────────────────

class VacancyListPageView(TemplateView):
    template_name = 'candidate/vacancy_list.html'


class VacancyDetailPageView(TemplateView):
    template_name = 'candidate/vacancy_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vacancy_id'] = kwargs.get('id')
        return context


class HRVacancyListPageView(TemplateView):
    template_name = 'hr/vacancy_list.html'


class HRVacancyFormPageView(TemplateView):
    template_name = 'hr/vacancy_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vacancy_id'] = kwargs.get('id')
        return context


class MatchPageView(TemplateView):
    """Template view for /match/ — the resume matching page."""
    template_name = 'candidate/match.html'
 