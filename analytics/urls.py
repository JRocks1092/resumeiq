"""
API URL patterns for analytics (under /api/analytics/).
"""

from django.urls import path
from .views import AnalyticsDetailView

urlpatterns = [
    path('<uuid:application_id>/', AnalyticsDetailView.as_view(), name='analytics-detail'),
]
