"""
Edge API URLs
"""
from django.urls import path
from .views import ProxyDecisionAPIView

urlpatterns = [
    # Decision API (ultra-fast)
    path('decision', ProxyDecisionAPIView.as_view(), name='decision'),
]
