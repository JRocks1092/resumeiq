"""
Views for the users app — API + template views.
"""

from users.permissions import IsHR
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.views.generic import TemplateView
from .serializers import RegisterSerializer, UserSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
User = get_user_model()


# ─── API Views ───────────────────────────────────────────────

class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ — Register a new user."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        data=request.data
        data["role"]="candidate"
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'message': 'User registered successfully.',
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )

class HRCreateUserView(generics.CreateAPIView):
    """POST /api/auth/register/ — Register a new user."""
    serializer_class = RegisterSerializer
    authentication_classes = [JWTAuthentication]  # Use JWT authentication
    permission_classes = [IsHR]

    def create(self, request, *args, **kwargs):
        data=request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'message': 'User registered successfully.',
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )






















class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/users/me/ — Get own profile
    PATCH /api/users/me/ — Update own profile
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# ─── Template Views ──────────────────────────────────────────

class LoginPageView(TemplateView):
    template_name = 'auth/login.html'


class RegisterPageView(TemplateView):
    template_name = 'auth/register.html'
   
class HRCreateUserPageView(TemplateView):
    """
    HR create user page view (template).
    """
    template_name = 'hr/create_user.html'