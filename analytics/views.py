"""
Views for the analytics app — API + template views.
"""

from rest_framework import generics, permissions
from rest_framework.response import Response
from django.views.generic import TemplateView
from users.permissions import IsHR
from applications.models import Application
from .models import Analytics
from .serializers import AnalyticsSerializer, ApplicantRankSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication


# ─── API Views ───────────────────────────────────────────────

class AnalyticsDetailView(generics.RetrieveAPIView):
    """GET /api/analytics/{application_id}/ — Full analysis (HR only)."""
    serializer_class = AnalyticsSerializer
    authentication_classes = [JWTAuthentication]  # Use JWT authentication
    permission_classes = [IsHR]

    def get_object(self):
        application_id = self.kwargs['application_id']
        return Analytics.objects.select_related(
            'application', 'application__user', 'application__vacancy'
        ).get(application_id=application_id)


class VacancyApplicantsView(generics.GenericAPIView):
    """GET /api/vacancies/{id}/applicants/ — Ranked applicants (HR only)."""
    permission_classes = [IsHR]

    def get(self, request, vacancy_id):
        applications = Application.objects.select_related(
            'user', 'analytics'
        ).filter(vacancy_id=vacancy_id).order_by('-applied_at')

        ranked = []
        unanalysed = []

        for app in applications:
            entry = {
                'application_id': app.id,
                'candidate_name': app.user.username,
                'candidate_email': app.user.email,
                'status': app.status,
                'applied_at': app.applied_at,
            }

            try:
                analytics = app.analytics
                entry['overall_score'] = analytics.overall_score
                entry['rating'] = analytics.rating
                ranked.append(entry)
            except Analytics.DoesNotExist:
                entry['overall_score'] = None
                entry['rating'] = 'N/A'
                unanalysed.append(entry)

        ranked.sort(key=lambda x: x['overall_score'], reverse=True)
        result = ranked + unanalysed

        serializer = ApplicantRankSerializer(result, many=True)
        return Response(serializer.data)


# ─── Template Views ──────────────────────────────────────────

class HRDashboardPageView(TemplateView):
    template_name = 'hr/dashboard.html'


class HRApplicantsListPageView(TemplateView):
    template_name = 'hr/applicants_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vacancy_id'] = kwargs.get('id')
        return context


class HRApplicantDetailPageView(TemplateView):
    template_name = 'hr/applicant_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['application_id'] = kwargs.get('id')
        return context
