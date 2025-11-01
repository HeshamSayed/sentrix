"""Application URLs"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from applications.views import ApplicationViewSet, EnvironmentViewSet
from applications.onboarding_wizard import OnboardingWizardViewSet

router = DefaultRouter()
router.register(r'', ApplicationViewSet, basename='application')
router.register(r'environments', EnvironmentViewSet, basename='environment')
router.register(r'onboarding-wizard', OnboardingWizardViewSet, basename='onboarding-wizard')

urlpatterns = router.urls
