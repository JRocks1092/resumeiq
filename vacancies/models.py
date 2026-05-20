"""
Models for the vacancies app.
"""

import uuid
from django.db import models
from django.conf import settings


class Vacancy(models.Model):
    """Job vacancy created by HR admin."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vacancies',
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    requirements = models.TextField()
    no_of_positions = models.IntegerField()
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vacancies'
        ordering = ['-created_at']
        verbose_name_plural = 'vacancies'

    def __str__(self):
        return self.title
