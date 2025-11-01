"""
Permission checking utilities and DRF permission classes
"""
from rest_framework import permissions


class HasPermission(permissions.BasePermission):
    """
    Custom permission class to check specific permissions
    Usage in views:
        permission_classes = [HasPermission]
        required_permissions = ['dashboard.view', 'users.manage']
    """
    
    def has_permission(self, request, view):
        # Anonymous users don't have permissions
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if view specifies required permissions
        required_permissions = getattr(view, 'required_permissions', [])
        
        if not required_permissions:
            # If no specific permissions required, allow authenticated users
            return True
        
        # Check if user has all required permissions
        for permission_code in required_permissions:
            if not request.user.has_permission(permission_code):
                return False
        
        return True


class HasAnyPermission(permissions.BasePermission):
    """
    Check if user has ANY of the required permissions (OR logic)
    Usage in views:
        permission_classes = [HasAnyPermission]
        required_permissions = ['users.view', 'users.manage']
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        required_permissions = getattr(view, 'required_permissions', [])
        
        if not required_permissions:
            return True
        
        # Check if user has at least one required permission
        for permission_code in required_permissions:
            if request.user.has_permission(permission_code):
                return True
        
        return False


def check_permission(user, permission_code):
    """
    Utility function to check a single permission
    """
    if not user or not user.is_authenticated:
        return False
    return user.has_permission(permission_code)


def check_permissions(user, permission_codes, require_all=True):
    """
    Utility function to check multiple permissions
    :param user: User object
    :param permission_codes: List of permission codes
    :param require_all: If True, user must have ALL permissions. If False, user must have ANY permission.
    """
    if not user or not user.is_authenticated:
        return False
    
    if require_all:
        return all(user.has_permission(code) for code in permission_codes)
    else:
        return any(user.has_permission(code) for code in permission_codes)


def get_user_permissions_dict(user):
    """
    Get all permissions for a user as a dictionary
    Useful for frontend to check permissions
    """
    if not user or not user.is_authenticated:
        return {}
    return user.get_all_permissions()

