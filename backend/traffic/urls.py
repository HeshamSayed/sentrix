from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import APIRequestViewSet, ThreatDetectionViewSet, BlockedIPViewSet, RateLimitRuleViewSet

router = DefaultRouter()
router.register(r'requests', APIRequestViewSet, basename='api-request')
router.register(r'threats', ThreatDetectionViewSet, basename='threat')
router.register(r'blocked-ips', BlockedIPViewSet, basename='blocked-ip')
router.register(r'rate-limits', RateLimitRuleViewSet, basename='rate-limit')

urlpatterns = [
    path('', include(router.urls)),
]

