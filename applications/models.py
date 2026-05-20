"""
Models for the applications app.
"""

import uuid
from django.db import models
from django.conf import settings


class Application(models.Model):
    """
    A candidate's application to a vacancy.
    Includes uploaded resume PDF and processing status.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('analysed', 'Analysed'),
        ('rejected', 'Rejected'),
        ('accepted', 'Accepted'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vacancy = models.ForeignKey(
        'vacancies.Vacancy',
        on_delete=models.CASCADE,
        related_name='applications',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications',
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default='pending')
    document_reference = models.TextField(help_text='Relative path to PDF in media/resumes/')

    class Meta:
        db_table = 'applications'
        ordering = ['-applied_at']
        unique_together = ['vacancy', 'user']

    def __str__(self):
        return f'{self.user.username} → {self.vacancy.title} ({self.status})'
