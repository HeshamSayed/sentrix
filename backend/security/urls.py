from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AnomalyDetectionViewSet,
    BlockedEntityViewSet,
    SecurityConfigurationViewSet,
    SecurityDashboardViewSet,
    UserBehaviorBaselineViewSet
)

router = DefaultRouter()
router.register(r'anomalies', AnomalyDetectionViewSet, basename='anomaly')
router.register(r'blocked', BlockedEntityViewSet, basename='blocked-entity')
router.register(r'config', SecurityConfigurationViewSet, basename='security-config')
router.register(r'dashboard', SecurityDashboardViewSet, basename='security-dashboard')
router.register(r'baselines', UserBehaviorBaselineViewSet, basename='behavior-baseline')

urlpatterns = [
    path('', include(router.urls)),
]

