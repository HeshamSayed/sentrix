from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MetricSnapshotViewSet, AlertViewSet, DashboardViewSet

router = DefaultRouter()
router.register(r'metrics', MetricSnapshotViewSet, basename='metric')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'dashboards', DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
]

