"""
Models for the analytics app.
"""

import uuid
from django.db import models


class Analytics(models.Model):
    """Stores AI analysis results for a resume application."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField(
        'applications.Application',
        on_delete=models.CASCADE,
        related_name='analytics',
    )
    vacancy_id = models.CharField(max_length=255)
    overall_score = models.IntegerField()
    rating = models.CharField(max_length=50)
    strengths = models.JSONField()
    areas_to_improve = models.JSONField()
    section_breakdown_percentage = models.JSONField()
    keyword_analysis = models.JSONField()
    projects = models.JSONField()
    experience = models.JSONField()
    final_summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'analytics'
        verbose_name_plural = 'analytics'

    def __str__(self):
        return f'Analytics for {self.application} — Score: {self.overall_score}'
