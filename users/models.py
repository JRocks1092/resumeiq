"""
Custom User model for the resume analyser platform.
Uses UUID primary keys and role-based access (candidate/hr).
"""

import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """Custom manager for User model."""

    def create_user(self, email, username, phone_number, password=None, role='candidate', **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        if not username:
            raise ValueError('Users must have a username')

        email = self.normalize_email(email)
        user = self.model(
            email=email,
            username=username,
            phone_number=phone_number,
            role=role,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, phone_number='', password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, username, phone_number, password, role='hr', **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model with UUID primary key.
    Two roles: 'candidate' and 'hr'.
    """

    ROLE_CHOICES = [
        ('candidate', 'Candidate'),
        ('hr', 'HR Admin'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=255)
    role = models.CharField(max_length=255, choices=ROLE_CHOICES, default='candidate')

    # Django auth fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'

    def __str__(self):
        return f'{self.username} ({self.email})'

    @property
    def is_hr(self):
        return self.role == 'hr'

    @property
    def is_candidate(self):
        return self.role == 'candidate'
