"""
Views for the applications app — API + template views.
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.views.generic import TemplateView
from users.permissions import IsHR, IsCandidate
from .models import Application
from .serializers import (
    ApplicationCreateSerializer,
    ApplicationListSerializer,
    ApplicationDetailSerializer,
    ApplicationStatusSerializer,
)


# ─── API Views ───────────────────────────────────────────────

class ApplicationCreateView(generics.CreateAPIView):
    """POST /api/applications/ — Submit application (candidate only)."""
    serializer_class = ApplicationCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsCandidate]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()

        from .tasks import analyse_resume
        analyse_resume.delay(str(application.id))

        return Response(
            {
                'message': 'Application submitted successfully. Analysis in progress.',
                'application': ApplicationListSerializer(application).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ApplicationListView(generics.ListAPIView):
    """GET /api/applications/list/ — Candidates see own, HR sees all."""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.user.is_hr:
            return ApplicationDetailSerializer
        return ApplicationListSerializer

    def get_queryset(self):
        if self.request.user.is_hr:
            return Application.objects.select_related('vacancy', 'user').all()
        return Application.objects.select_related('vacancy').filter(user=self.request.user)


class ApplicationDetailView(generics.RetrieveAPIView):
    """GET /api/applications/{id}/ — Detail view."""
    permission_classes = [permissions.IsAuthenticated]
    queryset = Application.objects.select_related('vacancy', 'user').all()

    def get_serializer_class(self):
        if self.request.user.is_hr:
            return ApplicationDetailSerializer
        return ApplicationListSerializer

    def get_object(self):
        obj = super().get_object()
        if self.request.user.is_candidate and obj.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You can only view your own applications.')
        return obj


class ApplicationStatusUpdateView(generics.UpdateAPIView):
    """PATCH /api/applications/{id}/status/ — HR only."""
    serializer_class = ApplicationStatusSerializer
    permission_classes = [permissions.IsAuthenticated, IsHR]
    queryset = Application.objects.all()


# ─── Template Views ──────────────────────────────────────────

class MyApplicationsPageView(TemplateView):
    template_name = 'candidate/my_applications.html'
