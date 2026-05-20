"""
Template URL patterns for analytics/HR pages.
"""

from django.urls import path
from .views import HRDashboardPageView, HRApplicantsListPageView, HRApplicantDetailPageView

urlpatterns = [
    path('hr/dashboard/', HRDashboardPageView.as_view(), name='hr-dashboard-page'),
    path('hr/vacancies/<uuid:id>/applicants/', HRApplicantsListPageView.as_view(), name='hr-applicants-list-page'),
    path('hr/applications/<uuid:id>/', HRApplicantDetailPageView.as_view(), name='hr-applicant-detail-page'),
]
