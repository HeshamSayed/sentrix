"""
Advanced permissions system for granular access control
"""
from django.db import models
from django.contrib.postgres.fields import ArrayField
from .models import User


class Permission(models.Model):
    """
    Defines available permissions in the system
    """
    CATEGORY_CHOICES = [
        ('PAGE', 'Page Access'),
        ('FEATURE', 'Feature Access'),
        ('ACTION', 'Action Permission'),
        ('DATA', 'Data Access'),
    ]
    
    code = models.CharField(max_length=100, unique=True, help_text="Unique permission code (e.g., 'dashboard.view')")
    name = models.CharField(max_length=255, help_text="Human-readable permission name")
    description = models.TextField(blank=True, help_text="Description of what this permission grants")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='FEATURE')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'code']
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class RolePermission(models.Model):
    """
    Default permissions for each role (ROOT, ADMIN, SECURITY)
    """
    ROLE_CHOICES = [
        ('ROOT', 'Root Administrator'),
        ('ADMIN', 'Administrator'),
        ('SECURITY', 'Security Analyst'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='role_permissions')
    is_default = models.BooleanField(default=True, help_text="If true, this permission is granted by default for this role")
    
    class Meta:
        unique_together = ['role', 'permission']
        verbose_name = 'Role Permission'
        verbose_name_plural = 'Role Permissions'
    
    def __str__(self):
        return f"{self.role} - {self.permission.code}"


class UserPermission(models.Model):
    """
    User-specific permission overrides
    Allows admins to grant/revoke specific permissions for individual users
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted = models.BooleanField(default=True, help_text="True = granted, False = revoked")
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='granted_permissions')
    granted_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, help_text="Reason for granting/revoking this permission")
    
    class Meta:
        unique_together = ['user', 'permission']
        ordering = ['-granted_at']
        verbose_name = 'User Permission'
        verbose_name_plural = 'User Permissions'
    
    def __str__(self):
        status = "Granted" if self.granted else "Revoked"
        return f"{self.user.email} - {self.permission.code} ({status})"


class PermissionGroup(models.Model):
    """
    Groups of permissions for easier management
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, related_name='groups')
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='permission_groups')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Permission Group'
        verbose_name_plural = 'Permission Groups'
    
    def __str__(self):
        return self.name


# Available permissions in the system
DEFAULT_PERMISSIONS = [
    # Page Access
    ('dashboard.view', 'View Dashboard', 'Access to main dashboard page', 'PAGE'),
    ('applications.view', 'View Applications', 'Access to applications page', 'PAGE'),
    ('applications.manage', 'Manage Applications', 'Create, edit, delete applications', 'PAGE'),
    ('users.view', 'View Users', 'Access to users page', 'PAGE'),
    ('users.manage', 'Manage Users', 'Create, edit, delete users', 'PAGE'),
    ('threats.view', 'View Threats', 'Access to threats page', 'PAGE'),
    ('threats.manage', 'Manage Threats', 'Resolve, acknowledge threats', 'PAGE'),
    ('traffic.view', 'View Traffic', 'Access to traffic page', 'PAGE'),
    ('analytics.view', 'View Analytics', 'Access to analytics page', 'PAGE'),
    ('alerts.view', 'View Alerts', 'Access to alerts page', 'PAGE'),
    ('alerts.manage', 'Manage Alerts', 'Acknowledge, resolve alerts', 'PAGE'),
    ('settings.view', 'View Settings', 'Access to settings page', 'PAGE'),
    ('settings.manage', 'Manage Settings', 'Update organization settings', 'PAGE'),
    
    # Feature Access
    ('quota.transfer', 'Transfer Quota', 'Transfer quota between applications', 'FEATURE'),
    ('quota.request', 'Request Quota', 'Request additional quota', 'FEATURE'),
    ('traffic.block', 'Block Traffic', 'Block IPs and regions', 'FEATURE'),
    ('maintenance.toggle', 'Toggle Maintenance', 'Enable/disable maintenance mode', 'FEATURE'),
    ('api_keys.manage', 'Manage API Keys', 'Create, revoke API keys', 'FEATURE'),
    ('export.data', 'Export Data', 'Export organization data', 'FEATURE'),
    ('billing.view', 'View Billing', 'Access billing information', 'FEATURE'),
    ('billing.manage', 'Manage Billing', 'Update payment methods, view invoices', 'FEATURE'),
    ('subscription.upgrade', 'Upgrade Subscription', 'Upgrade subscription plan', 'FEATURE'),
    
    # Action Permissions
    ('environment.create', 'Create Environment', 'Create new environments', 'ACTION'),
    ('environment.delete', 'Delete Environment', 'Delete environments', 'ACTION'),
    ('user.create', 'Create User', 'Create new users', 'ACTION'),
    ('user.delete', 'Delete User', 'Delete users', 'ACTION'),
    ('user.disable', 'Disable User', 'Enable/disable user accounts', 'ACTION'),
    ('permissions.manage', 'Manage Permissions', 'Modify user permissions', 'ACTION'),
    
    # Data Access
    ('data.sensitive', 'View Sensitive Data', 'Access to sensitive information', 'DATA'),
    ('data.export', 'Export Data', 'Export system data', 'DATA'),
    ('logs.view', 'View Logs', 'Access to system logs', 'DATA'),
    ('audit.view', 'View Audit Trail', 'Access to audit logs', 'DATA'),
]

# Default role permissions mapping
DEFAULT_ROLE_PERMISSIONS = {
    'ROOT': [
        # ROOT has ALL permissions
        'dashboard.view', 'applications.view', 'applications.manage', 'users.view', 'users.manage',
        'threats.view', 'threats.manage', 'traffic.view', 'analytics.view', 'alerts.view',
        'alerts.manage', 'settings.view', 'settings.manage', 'quota.transfer', 'quota.request',
        'traffic.block', 'maintenance.toggle', 'api_keys.manage', 'export.data', 'billing.view',
        'billing.manage', 'subscription.upgrade', 'environment.create', 'environment.delete',
        'user.create', 'user.delete', 'user.disable', 'permissions.manage', 'data.sensitive',
        'data.export', 'logs.view', 'audit.view',
    ],
    'ADMIN': [
        # ADMIN has most permissions except sensitive operations
        'dashboard.view', 'applications.view', 'applications.manage', 'users.view', 'users.manage',
        'threats.view', 'threats.manage', 'traffic.view', 'analytics.view', 'alerts.view',
        'alerts.manage', 'settings.view', 'quota.transfer', 'quota.request', 'traffic.block',
        'maintenance.toggle', 'environment.create', 'environment.delete', 'user.create',
        'user.disable', 'data.export', 'logs.view',
    ],
    'SECURITY': [
        # SECURITY focused on monitoring and analysis
        'dashboard.view', 'applications.view', 'threats.view', 'threats.manage', 'traffic.view',
        'analytics.view', 'alerts.view', 'alerts.manage', 'traffic.block', 'logs.view',
    ],
}

