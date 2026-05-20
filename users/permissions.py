"""
Custom permissions for the users app.
"""

from rest_framework.permissions import BasePermission


class IsHR(BasePermission):
    """Allows access only to HR admin users."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'hr'
        )


class IsCandidate(BasePermission):
    """Allows access only to candidate users."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'candidate'
        )
