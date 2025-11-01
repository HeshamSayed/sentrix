from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrganizationViewSet
from .settings_views import (
    OrganizationSettingsView,
    NotificationSettingsView,
    TestNotificationView,
    SecuritySettingsView,
    SubscriptionInfoView,
    APIKeysView,
    CreateAPIKeyView,
    RevokeAPIKeyView,
    ExportDataView,
    DeleteOrganizationView,
    UpgradePlanView,
    ViewInvoicesView,
    DownloadInvoiceView,
    UpdatePaymentMethodView,
)

router = DefaultRouter()
router.register(r'', OrganizationViewSet, basename='organization')

urlpatterns = [
    # Settings endpoints (must come before router to avoid conflicts)
    path('settings/', OrganizationSettingsView.as_view(), name='organization-settings'),
    path('notifications/', NotificationSettingsView.as_view(), name='notification-settings'),
    path('test_notification/', TestNotificationView.as_view(), name='test-notification'),
    path('security/', SecuritySettingsView.as_view(), name='security-settings'),
    path('subscription/', SubscriptionInfoView.as_view(), name='subscription-info'),
    path('api_keys/', APIKeysView.as_view(), name='api-keys'),
    path('create_api_key/', CreateAPIKeyView.as_view(), name='create-api-key'),
    path('revoke_api_key/', RevokeAPIKeyView.as_view(), name='revoke-api-key'),
    path('export_data/', ExportDataView.as_view(), name='export-data'),
    path('delete_organization/', DeleteOrganizationView.as_view(), name='delete-organization'),
    
    # Subscription & Billing endpoints
    path('upgrade_plan/', UpgradePlanView.as_view(), name='upgrade-plan'),
    path('invoices/', ViewInvoicesView.as_view(), name='view-invoices'),
    path('invoices/<str:invoice_id>/download/', DownloadInvoiceView.as_view(), name='download-invoice'),
    path('payment_method/', UpdatePaymentMethodView.as_view(), name='update-payment-method'),
    
    # Router patterns
    path('', include(router.urls)),
]
