"""
Serializers for the vacancies app.
"""

from rest_framework import serializers
from .models import Vacancy


class VacancySerializer(serializers.ModelSerializer):
    """Full vacancy serializer."""

    admin_name = serializers.CharField(source='admin.username', read_only=True)

    class Meta:
        model = Vacancy
        fields = [
            'id', 'admin', 'admin_name', 'title', 'description',
            'requirements', 'no_of_positions', 'date', 'created_at',
        ]
        read_only_fields = ['id', 'admin', 'admin_name', 'created_at']

    def create(self, validated_data):
        validated_data['admin'] = self.context['request'].user
        return super().create(validated_data)


class VacancyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for vacancy listings."""

    class Meta:
        model = Vacancy
        fields = ['id', 'title', 'no_of_positions', 'date', 'created_at']
