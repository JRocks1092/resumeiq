"""
Serializers for the analytics app.
"""

from rest_framework import serializers
from .models import Analytics


class AnalyticsSerializer(serializers.ModelSerializer):
    """Full analytics serializer for HR view."""

    application_id = serializers.UUIDField(source='application.id', read_only=True)
    candidate_name = serializers.CharField(source='application.user.username', read_only=True)
    candidate_email = serializers.CharField(source='application.user.email', read_only=True)
    vacancy_title = serializers.CharField(source='application.vacancy.title', read_only=True)

    class Meta:
        model = Analytics
        fields = [
            'id', 'application_id', 'candidate_name', 'candidate_email',
            'vacancy_title', 'vacancy_id', 'overall_score', 'rating',
            'strengths', 'areas_to_improve', 'section_breakdown_percentage',
            'keyword_analysis', 'projects', 'experience', 'final_summary',
            'created_at',
        ]
        read_only_fields = fields


class ApplicantRankSerializer(serializers.Serializer):
    """Serializer for ranked applicant list."""

    application_id = serializers.UUIDField()
    candidate_name = serializers.CharField()
    candidate_email = serializers.CharField()
    overall_score = serializers.IntegerField(allow_null=True)
    rating = serializers.CharField()
    status = serializers.CharField()
    applied_at = serializers.DateTimeField()
