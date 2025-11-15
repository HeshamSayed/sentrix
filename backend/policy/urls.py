"""
Policy API URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PolicyViewSet, PolicyTestView

# Create router for viewsets
router = DefaultRouter()
router.register(r'policies', PolicyViewSet, basename='policy')

urlpatterns = [
    # ViewSet routes (CRUD + custom actions)
    path('', include(router.urls)),

    # Test endpoint
    path('policies/test/', PolicyTestView.as_view(), name='policy-test'),
]
