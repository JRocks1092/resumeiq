"""
Serializers for the users app.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'password', 'role']
        read_only_fields = ['id']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile."""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'role']
        read_only_fields = ['id', 'role']
