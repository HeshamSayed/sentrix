"""
DRF serializers for core models.
"""
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import Organization, Subscription, User, Application, APIEndpoint, UsageTracking


class OrganizationSerializer(serializers.ModelSerializer):
    """Organization serializer"""

    class Meta:
        model = Organization
        fields = [
            'org_id',
            'name',
            'slug',
            'default_config',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['org_id', 'created_at', 'updated_at']


class SubscriptionSerializer(serializers.ModelSerializer):
    """Subscription serializer"""

    org_name = serializers.CharField(source='org.name', read_only=True)

    class Meta:
        model = Subscription
        fields = [
            'subscription_id',
            'org',
            'org_name',
            'plan_tier',
            'quota_max_applications',
            'quota_max_users',
            'quota_requests_per_month',
            'features',
            'valid_from',
            'valid_until',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['subscription_id', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    """User serializer (for responses)"""

    org_name = serializers.CharField(source='org.name', read_only=True)

    class Meta:
        model = User
        fields = [
            'user_id',
            'org',
            'org_name',
            'email',
            'full_name',
            'role',
            'is_active',
            'last_login',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['user_id', 'last_login', 'created_at', 'updated_at']


class UserCreateSerializer(serializers.ModelSerializer):
    """User serializer for creation (includes password)"""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            'org',
            'email',
            'password',
            'full_name',
            'role'
        ]

    def create(self, validated_data):
        """Hash password before saving"""
        password = validated_data.pop('password')
        validated_data['password_hash'] = make_password(password)
        return super().create(validated_data)


class LoginSerializer(serializers.Serializer):
    """Login request serializer"""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class TokenSerializer(serializers.Serializer):
    """Token response serializer"""

    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    user = UserSerializer()


class ApplicationSerializer(serializers.ModelSerializer):
    """Application serializer"""

    org_name = serializers.CharField(source='org.name', read_only=True)
    merged_config = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            'app_id',
            'org',
            'org_name',
            'name',
            'slug',
            'domain',
            'origin_url',
            'cname_target',
            'verification_token',
            'dns_verified',
            'dns_verified_at',
            'custom_config',
            'merged_config',
            'failover_mode',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'app_id',
            'verification_token',
            'dns_verified',
            'dns_verified_at',
            'created_at',
            'updated_at'
        ]

    def get_merged_config(self, obj):
        """Return merged configuration"""
        return obj.get_merged_config()


class APIEndpointSerializer(serializers.ModelSerializer):
    """API Endpoint serializer"""

    app_name = serializers.CharField(source='app.name', read_only=True)
    org_name = serializers.CharField(source='org.name', read_only=True)

    class Meta:
        model = APIEndpoint
        fields = [
            'endpoint_id',
            'org',
            'org_name',
            'app',
            'app_name',
            'method',
            'path_pattern',
            'request_schema',
            'response_schema',
            'owner',
            'tags',
            'risk_score',
            'first_seen',
            'last_seen',
            'request_count',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'endpoint_id',
            'first_seen',
            'last_seen',
            'request_count',
            'created_at',
            'updated_at'
        ]


class UsageTrackingSerializer(serializers.ModelSerializer):
    """Usage tracking serializer"""

    org_name = serializers.CharField(source='org.name', read_only=True)
    app_name = serializers.CharField(source='app.name', read_only=True)

    class Meta:
        model = UsageTracking
        fields = [
            'usage_id',
            'org',
            'org_name',
            'app',
            'app_name',
            'period_start',
            'period_end',
            'request_count',
            'blocked_count',
            'r1_invocation_count',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['usage_id', 'created_at', 'updated_at']
