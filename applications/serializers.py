"""
Serializers for the applications app.
"""

import os
import uuid as uuid_lib
from rest_framework import serializers
from django.conf import settings
from .models import Application


class ApplicationCreateSerializer(serializers.Serializer):
    """Handles multipart form data: vacancy_id + resume PDF."""

    vacancy_id = serializers.UUIDField()
    resume = serializers.FileField()

    def validate_resume(self, value):
        if not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError('Only PDF files are accepted.')
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError('File size must not exceed 10MB.')
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        vacancy_id = validated_data['vacancy_id']
        resume = validated_data['resume']

        if Application.objects.filter(vacancy_id=vacancy_id, user=user).exists():
            raise serializers.ValidationError('You have already applied to this vacancy.')

        filename = f'{uuid_lib.uuid4()}.pdf'
        relative_path = os.path.join('resumes', filename)
        absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)

        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
        with open(absolute_path, 'wb+') as f:
            for chunk in resume.chunks():
                f.write(chunk)

        application = Application.objects.create(
            vacancy_id=vacancy_id,
            user=user,
            status='pending',
            document_reference=relative_path,
        )
        return application


class ApplicationListSerializer(serializers.ModelSerializer):
    """Candidate view — limited fields."""

    vacancy_title = serializers.CharField(source='vacancy.title', read_only=True)

    class Meta:
        model = Application
        fields = ['id', 'vacancy', 'vacancy_title', 'status', 'applied_at']
        read_only_fields = fields


class ApplicationDetailSerializer(serializers.ModelSerializer):
    """Full serializer for HR view."""

    vacancy_title = serializers.CharField(source='vacancy.title', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)

    class Meta:
        model = Application
        fields = [
            'id', 'vacancy', 'vacancy_title', 'user', 'user_name',
            'user_email', 'user_phone', 'status', 'applied_at',
            'document_reference',
        ]
        read_only_fields = fields


class ApplicationStatusSerializer(serializers.ModelSerializer):
    """For updating application status (HR only)."""

    class Meta:
        model = Application
        fields = ['status']
