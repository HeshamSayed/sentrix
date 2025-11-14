"""
Role-based access control (RBAC) permissions.
"""

# Permission definitions by role
PERMISSIONS = {
    'admin': ['*'],  # All permissions

    'analyst': [
        'view_events',
        'view_endpoints',
        'view_detections',
        'view_policies',
        'create_policy',
        'update_policy',
        'simulate_policy',
        'update_detection_status',
        'assign_detection',
        'view_audit_logs',
    ],

    'viewer': [
        'view_events',
        'view_endpoints',
        'view_detections',
        'view_policies',
    ]
}


def check_permission(user_role: str, permission: str) -> bool:
    """
    Check if a role has a specific permission.

    Args:
        user_role: User role (admin, analyst, viewer)
        permission: Permission name (e.g., 'create_policy')

    Returns:
        True if role has permission, False otherwise
    """
    allowed = PERMISSIONS.get(user_role, [])
    return '*' in allowed or permission in allowed
