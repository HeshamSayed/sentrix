"""
Views for permission management
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from core.permissions import IsRoot, IsRootOrAdmin
from .permissions_models import Permission, RolePermission, UserPermission, PermissionGroup
from .permissions_serializers import (
    PermissionSerializer, RolePermissionSerializer, UserPermissionSerializer,
    PermissionGroupSerializer, UserPermissionsDetailSerializer, UpdateUserPermissionsSerializer
)
from .models import User


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing available permissions
    Read-only as permissions are system-defined
    """
    queryset = Permission.objects.filter(is_active=True)
    serializer_class = PermissionSerializer
    permission_classes = [IsRootOrAdmin]
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get permissions grouped by category"""
        permissions = Permission.objects.filter(is_active=True)
        
        grouped = {}
        for perm in permissions:
            if perm.category not in grouped:
                grouped[perm.category] = []
            grouped[perm.category].append(PermissionSerializer(perm).data)
        
        return Response(grouped)


class RolePermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing role-based default permissions
    Read-only as role permissions are system-defined
    """
    queryset = RolePermission.objects.select_related('permission').all()
    serializer_class = RolePermissionSerializer
    permission_classes = [IsRootOrAdmin]
    
    @action(detail=False, methods=['get'])
    def by_role(self, request):
        """Get permissions for each role"""
        from .permissions_models import DEFAULT_ROLE_PERMISSIONS
        
        result = {}
        for role in ['ROOT', 'ADMIN', 'SECURITY']:
            result[role] = DEFAULT_ROLE_PERMISSIONS.get(role, [])
        
        return Response(result)


class UserPermissionsView(APIView):
    """
    View for managing user-specific permission overrides
    """
    permission_classes = [IsRootOrAdmin]
    
    def get(self, request, user_id=None):
        """
        Get permissions for a specific user or all users
        """
        if user_id:
            # Get specific user's permissions
            user = get_object_or_404(User, id=user_id, organization=request.user.organization)
            serializer = UserPermissionsDetailSerializer(user)
            return Response(serializer.data)
        else:
            # List all users with their permissions
            users = User.objects.filter(organization=request.user.organization)
            serializer = UserPermissionsDetailSerializer(users, many=True)
            return Response(serializer.data)
    
    def patch(self, request, user_id):
        """
        Update permissions for a specific user
        Only ROOT can update permissions
        """
        if not request.user.is_root:
            return Response({
                'error': 'Only ROOT users can modify permissions'
            }, status=status.HTTP_403_FORBIDDEN)
        
        user = get_object_or_404(User, id=user_id, organization=request.user.organization)
        
        # Don't allow modifying ROOT user permissions
        if user.is_root and user != request.user:
            return Response({
                'error': 'Cannot modify ROOT user permissions'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = UpdateUserPermissionsSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update user permissions
        permissions = serializer.validated_data['permissions']
        reason = serializer.validated_data.get('reason', '')
        
        # Merge with existing permissions
        current_perms = user.permissions or {}
        current_perms.update(permissions)
        user.permissions = current_perms
        user.save()
        
        # Log permission changes
        for perm_code, granted in permissions.items():
            try:
                permission = Permission.objects.get(code=perm_code)
                UserPermission.objects.update_or_create(
                    user=user,
                    permission=permission,
                    defaults={
                        'granted': granted,
                        'granted_by': request.user,
                        'reason': reason
                    }
                )
            except Permission.DoesNotExist:
                pass
        
        # Return updated permissions
        result_serializer = UserPermissionsDetailSerializer(user)
        return Response(result_serializer.data)


class BulkUpdatePermissionsView(APIView):
    """
    Bulk update permissions for multiple users
    """
    permission_classes = [IsRoot]
    
    def post(self, request):
        """
        Bulk update permissions
        Expected data: {
            "user_ids": [1, 2, 3],
            "permissions": {"dashboard.view": true, "users.manage": false},
            "reason": "Adjust permissions for security team"
        }
        """
        user_ids = request.data.get('user_ids', [])
        permissions = request.data.get('permissions', {})
        reason = request.data.get('reason', '')
        
        if not user_ids or not permissions:
            return Response({
                'error': 'user_ids and permissions are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        users = User.objects.filter(
            id__in=user_ids,
            organization=request.user.organization
        ).exclude(role='ROOT')  # Don't modify ROOT users
        
        updated_count = 0
        for user in users:
            current_perms = user.permissions or {}
            current_perms.update(permissions)
            user.permissions = current_perms
            user.save()
            
            # Log changes
            for perm_code, granted in permissions.items():
                try:
                    permission = Permission.objects.get(code=perm_code)
                    UserPermission.objects.update_or_create(
                        user=user,
                        permission=permission,
                        defaults={
                            'granted': granted,
                            'granted_by': request.user,
                            'reason': reason
                        }
                    )
                except Permission.DoesNotExist:
                    pass
            
            updated_count += 1
        
        return Response({
            'message': f'Updated permissions for {updated_count} users',
            'updated_users': updated_count
        })


class ResetUserPermissionsView(APIView):
    """
    Reset user permissions to role defaults
    """
    permission_classes = [IsRoot]
    
    def post(self, request, user_id):
        """
        Reset user permissions to their role defaults
        """
        user = get_object_or_404(User, id=user_id, organization=request.user.organization)
        
        if user.is_root:
            return Response({
                'error': 'Cannot reset ROOT user permissions'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Clear custom permissions
        user.permissions = {}
        user.save()
        
        # Delete UserPermission records
        UserPermission.objects.filter(user=user).delete()
        
        return Response({
            'message': f'Permissions reset to {user.role} defaults',
            'user': UserPermissionsDetailSerializer(user).data
        })


class PermissionGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing permission groups
    """
    serializer_class = PermissionGroupSerializer
    permission_classes = [IsRootOrAdmin]
    
    def get_queryset(self):
        return PermissionGroup.objects.filter(
            organization=self.request.user.organization
        ).prefetch_related('permissions')
    
    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def apply_to_users(self, request, pk=None):
        """
        Apply permission group to multiple users
        Expected data: {"user_ids": [1, 2, 3]}
        """
        group = self.get_object()
        user_ids = request.data.get('user_ids', [])
        
        if not user_ids:
            return Response({
                'error': 'user_ids is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        users = User.objects.filter(
            id__in=user_ids,
            organization=request.user.organization
        )
        
        # Get all permissions in this group
        group_permissions = {perm.code: True for perm in group.permissions.all()}
        
        updated_count = 0
        for user in users:
            current_perms = user.permissions or {}
            current_perms.update(group_permissions)
            user.permissions = current_perms
            user.save()
            updated_count += 1
        
        return Response({
            'message': f'Applied permission group to {updated_count} users',
            'updated_users': updated_count
        })

