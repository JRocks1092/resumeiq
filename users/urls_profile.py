"""
API URL patterns for user profile (under /api/users/).
"""

from django.urls import path
from .views import UserProfileView

urlpatterns = [
    path('me/', UserProfileView.as_view(), name='user-profile'),
]
