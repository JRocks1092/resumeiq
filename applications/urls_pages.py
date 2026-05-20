"""
Template URL patterns for application pages.
"""

from django.urls import path
from .views import MyApplicationsPageView

urlpatterns = [
    path('my-applications/', MyApplicationsPageView.as_view(), name='my-applications-page'),
]
