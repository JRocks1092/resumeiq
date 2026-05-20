"""
API URL patterns for applications (under /api/applications/).
"""

from django.urls import path
from .views import (
    ApplicationCreateView,
    ApplicationListView,
    ApplicationDetailView,
    ApplicationStatusUpdateView,
)

urlpatterns = [
    path('', ApplicationCreateView.as_view(), name='application-create'),
    path('list/', ApplicationListView.as_view(), name='application-list'),
    path('<uuid:pk>/', ApplicationDetailView.as_view(), name='application-detail'),
    path('<uuid:pk>/status/', ApplicationStatusUpdateView.as_view(), name='application-status-update'),
]
