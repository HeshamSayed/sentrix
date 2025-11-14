"""
Health check URLs
"""
from django.http import JsonResponse
from django.urls import path


def health_check(request):
    """Simple health check endpoint"""
    return JsonResponse({"status": "healthy"})


urlpatterns = [
    path('', health_check, name='health'),
]
