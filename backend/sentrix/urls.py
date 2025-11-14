"""
Sentrix URL Configuration
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # API v1
    path('v1/', include([
        path('', include('core.urls')),
        path('edge/', include('edge.urls')),
        path('detection/', include('detection.urls')),
        path('policy/', include('policy.urls')),
    ])),

    # Health check
    path('health/', include('core.urls_health')),
]
