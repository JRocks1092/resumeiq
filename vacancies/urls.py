"""
API URL patterns for vacancies (under /api/vacancies/).
"""

from django.urls import path
from .views import VacancyListCreateView, VacancyDetailView
from analytics.views import VacancyApplicantsView

urlpatterns = [
    path('', VacancyListCreateView.as_view(), name='vacancy-list-create'),
    path('<uuid:pk>/', VacancyDetailView.as_view(), name='vacancy-detail'),
    path('<uuid:vacancy_id>/applicants/', VacancyApplicantsView.as_view(), name='vacancy-applicants'),
]
