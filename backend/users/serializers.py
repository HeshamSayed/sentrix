from rest_framework import serializers
from .models import User, APIKey, AuditLog

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    is_root = serializers.ReadOnlyField()
    is_admin = serializers.ReadOnlyField()
    can_manage_users = serializers.ReadOnlyField()
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    all_permissions = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'organization', 'organization_name', 'role', 'is_active',
            'is_licensed', 'is_root', 'is_admin', 'can_manage_users',
            'permissions', 'all_permissions', 'last_login', 'last_login_ip', 'login_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_login', 'last_login_ip', 'login_count']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def get_all_permissions(self, obj):
        """Get all effective permissions for this user"""
        return obj.get_all_permissions()

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'role', 'permissions']
    
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = [
            'id', 'user', 'name', 'key', 'is_active',
            'last_used_at', 'expires_at', 'rate_limit', 'created_at'
        ]
        read_only_fields = ['id', 'key', 'last_used_at', 'created_at']

class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_email', 'organization', 'action',
            'resource_type', 'resource_id', 'ip_address', 'user_agent',
            'details', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

