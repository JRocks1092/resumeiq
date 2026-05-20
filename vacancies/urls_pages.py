"""
Template URL patterns for vacancy pages.
"""

from django.urls import path
from .views import (
    VacancyListPageView,
    VacancyDetailPageView,
    HRVacancyListPageView,
    HRVacancyFormPageView,
)

urlpatterns = [
    path('vacancies/', VacancyListPageView.as_view(), name='vacancy-list-page'),
    path('vacancies/<uuid:id>/', VacancyDetailPageView.as_view(), name='vacancy-detail-page'),
    path('hr/vacancies/', HRVacancyListPageView.as_view(), name='hr-vacancy-list-page'),
    path('hr/vacancies/create/', HRVacancyFormPageView.as_view(), name='hr-vacancy-create-page'),
    path('hr/vacancies/<uuid:id>/edit/', HRVacancyFormPageView.as_view(), name='hr-vacancy-edit-page'),    

]
