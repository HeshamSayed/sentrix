from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, APIKeyViewSet, AuditLogViewSet
from .permissions_views import (
    PermissionViewSet, RolePermissionViewSet, PermissionGroupViewSet,
    UserPermissionsView, BulkUpdatePermissionsView, ResetUserPermissionsView
)

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')
router.register(r'api-keys', APIKeyViewSet, basename='api-key')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

# Permission management routes
router.register(r'permissions', PermissionViewSet, basename='permission')
router.register(r'role-permissions', RolePermissionViewSet, basename='role-permission')
router.register(r'permission-groups', PermissionGroupViewSet, basename='permission-group')

urlpatterns = [
    # User permissions management
    path('permissions/user/', UserPermissionsView.as_view(), name='user-permissions-list'),
    path('permissions/user/<int:user_id>/', UserPermissionsView.as_view(), name='user-permissions-detail'),
    path('permissions/bulk-update/', BulkUpdatePermissionsView.as_view(), name='bulk-update-permissions'),
    path('permissions/reset/<int:user_id>/', ResetUserPermissionsView.as_view(), name='reset-user-permissions'),
    
    # Router patterns
    path('', include(router.urls)),
]

