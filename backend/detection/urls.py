"""
Detection API URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'detections', views.DetectionEventViewSet, basename='detection')

urlpatterns = [
    path('', include(router.urls)),
]
