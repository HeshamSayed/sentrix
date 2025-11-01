"""
Serializers for permission management
"""
from rest_framework import serializers
from .permissions_models import Permission, RolePermission, UserPermission, PermissionGroup
from .models import User


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer for Permission model"""
    
    class Meta:
        model = Permission
        fields = ['id', 'code', 'name', 'description', 'category', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class RolePermissionSerializer(serializers.ModelSerializer):
    """Serializer for RolePermission model"""
    permission_code = serializers.CharField(source='permission.code', read_only=True)
    permission_name = serializers.CharField(source='permission.name', read_only=True)
    
    class Meta:
        model = RolePermission
        fields = ['id', 'role', 'permission', 'permission_code', 'permission_name', 'is_default']


class UserPermissionSerializer(serializers.ModelSerializer):
    """Serializer for UserPermission model"""
    permission_code = serializers.CharField(source='permission.code', read_only=True)
    permission_name = serializers.CharField(source='permission.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    granted_by_email = serializers.EmailField(source='granted_by.email', read_only=True)
    
    class Meta:
        model = UserPermission
        fields = [
            'id', 'user', 'user_email', 'permission', 'permission_code',
            'permission_name', 'granted', 'granted_by', 'granted_by_email',
            'granted_at', 'reason'
        ]
        read_only_fields = ['id', 'granted_at', 'granted_by']


class PermissionGroupSerializer(serializers.ModelSerializer):
    """Serializer for PermissionGroup model"""
    permissions_count = serializers.SerializerMethodField()
    permission_codes = serializers.SerializerMethodField()
    
    class Meta:
        model = PermissionGroup
        fields = [
            'id', 'name', 'description', 'permissions', 'permissions_count',
            'permission_codes', 'organization', 'created_by', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'created_by', 'organization']
    
    def get_permissions_count(self, obj):
        return obj.permissions.count()
    
    def get_permission_codes(self, obj):
        return list(obj.permissions.values_list('code', flat=True))


class UserPermissionsDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer showing all user permissions"""
    all_permissions = serializers.SerializerMethodField()
    custom_permissions = serializers.SerializerMethodField()
    role_permissions = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role',
            'all_permissions', 'custom_permissions', 'role_permissions'
        ]
        read_only_fields = ['id', 'email']
    
    def get_all_permissions(self, obj):
        """Get all effective permissions for this user"""
        return obj.get_all_permissions()
    
    def get_custom_permissions(self, obj):
        """Get custom permission overrides"""
        return obj.permissions
    
    def get_role_permissions(self, obj):
        """Get default role-based permissions"""
        from .permissions_models import DEFAULT_ROLE_PERMISSIONS
        role_perms = DEFAULT_ROLE_PERMISSIONS.get(obj.role, [])
        return role_perms


class UpdateUserPermissionsSerializer(serializers.Serializer):
    """Serializer for updating user permissions"""
    user_id = serializers.IntegerField()
    permissions = serializers.DictField(
        child=serializers.BooleanField(),
        help_text="Dict of permission codes to boolean values"
    )
    reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate_user_id(self, value):
        """Validate user exists"""
        try:
            user = User.objects.get(id=value)
            # Check if user is in the same organization
            request_user = self.context.get('request').user
            if user.organization != request_user.organization:
                raise serializers.ValidationError("User not in your organization")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
    
    def validate_permissions(self, value):
        """Validate permission codes exist"""
        from .permissions_models import DEFAULT_PERMISSIONS
        valid_codes = [perm[0] for perm in DEFAULT_PERMISSIONS]
        
        for code in value.keys():
            if code not in valid_codes:
                raise serializers.ValidationError(f"Invalid permission code: {code}")
        
        return value

