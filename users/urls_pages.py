"""
Template URL patterns for auth pages.
"""

from django.urls import path
from .views import LoginPageView, RegisterPageView,HRCreateUserPageView

urlpatterns = [
    path('', LoginPageView.as_view(), name='login-page'),
    path('register/', RegisterPageView.as_view(), name='register-page'),
    path('hr/create-user/', HRCreateUserPageView.as_view(), name='create-user-page'),
]
