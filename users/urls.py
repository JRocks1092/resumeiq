"""
API URL patterns for authentication (under /api/auth/).
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView,HRCreateUserView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', TokenObtainPairView.as_view(), name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('hr/create-user/', HRCreateUserView.as_view(), name='hr-create-user-page'),
]
