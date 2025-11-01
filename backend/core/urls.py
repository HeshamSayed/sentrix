"""Core URLs for onboarding"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views.onboarding import OnboardingViewSet

router = DefaultRouter()
router.register(r'onboarding', OnboardingViewSet, basename='onboarding')

urlpatterns = router.urls

