from rest_framework import permissions

class IsRootUser(permissions.BasePermission):
    """Permission check for root users"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'ROOT'

class IsAdminUser(permissions.BasePermission):
    """Permission check for admin users"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['ROOT', 'ADMIN']

class IsSecurityUser(permissions.BasePermission):
    """Permission check for security users"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['ROOT', 'ADMIN', 'SECURITY']

class IsSameOrganization(permissions.BasePermission):
    """Check if user belongs to the same organization"""
    def has_object_permission(self, request, view, obj):
        if not hasattr(obj, 'organization'):
            return True
        return obj.organization == request.user.organization

class CanManageUsers(permissions.BasePermission):
    """Check if user can manage other users"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['ROOT', 'ADMIN']

# Aliases for convenience
IsRoot = IsRootUser
IsRootOrAdmin = IsAdminUser
IsAdmin = IsAdminUser

