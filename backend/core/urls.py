"""
Core API URLs - Organizations, Applications, Users
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import dashboard

# Create router and register viewsets
router = DefaultRouter()
router.register(r'organizations', views.OrganizationViewSet, basename='organization')
router.register(r'subscriptions', views.SubscriptionViewSet, basename='subscription')
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'applications', views.ApplicationViewSet, basename='application')
router.register(r'endpoints', views.APIEndpointViewSet, basename='endpoint')
router.register(r'usage', views.UsageTrackingViewSet, basename='usage')

urlpatterns = [
    # Authentication
    path('auth/login/', views.login, name='login'),
    path('auth/me/', views.me, name='me'),

    # Dashboard
    path('dashboard/summary/', dashboard.dashboard_summary, name='dashboard-summary'),
    path('dashboard/metrics/', dashboard.metrics_timeseries, name='dashboard-metrics'),

    # Router URLs
    path('', include(router.urls)),
]
