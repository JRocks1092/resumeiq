"""
Views for the vacancies app — API + template views.
"""

from django.utils.timezone import now
from rest_framework import generics, permissions
from django.views.generic import TemplateView
from users.permissions import IsHR
from .models import Vacancy
from .serializers import VacancySerializer, VacancyListSerializer,AvailableVacancyListSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response

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
 