"""
Root URL configuration for resumeanalyser project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # API endpoints
    path('api/auth/', include('users.urls')),
    path('api/users/', include('users.urls_profile')),
    path('api/vacancies/', include('vacancies.urls')),
    path('api/applications/', include('applications.urls')),
    path('api/analytics/', include('analytics.urls')),

    # Template views (pages)
    path('', include('users.urls_pages')),
    path('', include('vacancies.urls_pages')),
    path('', include('applications.urls_pages')),
    path('', include('analytics.urls_pages')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
