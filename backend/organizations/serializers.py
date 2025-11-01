from rest_framework import serializers
from .models import Organization, OrganizationInvite
from users.models import User


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model"""
    quota_percentage = serializers.ReadOnlyField()
    remaining_quota = serializers.ReadOnlyField()
    can_add_user = serializers.ReadOnlyField()
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'description', 
            'subscription_tier', 'is_active',
            'subscription_starts_at', 'subscription_ends_at',
            'max_users', 'current_users', 'can_add_user',
            'global_quota', 'used_quota', 'quota_percentage', 'remaining_quota',
            'billing_email', 'stripe_customer_id', 'stripe_subscription_id',
            'settings', 'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'stripe_customer_id', 'stripe_subscription_id', 'created_at', 'updated_at']


class OrganizationSettingsSerializer(serializers.Serializer):
    """Serializer for organization general settings"""
    name = serializers.CharField(max_length=255)
    billing_email = serializers.EmailField()
    description = serializers.CharField(required=False, allow_blank=True)
    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class NotificationSettingsSerializer(serializers.Serializer):
    """Serializer for notification settings"""
    email_alerts = serializers.BooleanField(default=True)
    slack_notifications = serializers.BooleanField(default=False)
    webhook_url = serializers.URLField(required=False, allow_blank=True)
    alert_threshold = serializers.ChoiceField(
        choices=['all', 'high', 'critical'],
        default='high'
    )
    
    def update(self, instance, validated_data):
        # Store in settings JSON field
        settings = instance.settings or {}
        settings['notifications'] = validated_data
        instance.settings = settings
        instance.save()
        return validated_data


class SecuritySettingsSerializer(serializers.Serializer):
    """Serializer for security settings"""
    two_factor_enabled = serializers.BooleanField(default=False)
    session_timeout = serializers.ChoiceField(
        choices=['15', '30', '60', 'never'],
        default='30'
    )
    ip_whitelist = serializers.ListField(
        child=serializers.IPAddressField(),
        required=False,
        default=list
    )
    
    def update(self, instance, validated_data):
        settings = instance.settings or {}
        settings['security'] = validated_data
        instance.settings = settings
        instance.save()
        return validated_data


class APIKeySerializer(serializers.Serializer):
    """Serializer for API key management"""
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=100)
    key = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    last_used_at = serializers.DateTimeField(read_only=True, allow_null=True)
    is_active = serializers.BooleanField(default=True)


class SubscriptionInfoSerializer(serializers.Serializer):
    """Serializer for subscription information"""
    tier = serializers.CharField(source='subscription_tier')
    is_active = serializers.BooleanField()
    starts_at = serializers.DateTimeField(source='subscription_starts_at', allow_null=True)
    ends_at = serializers.DateTimeField(source='subscription_ends_at', allow_null=True)
    quota_limit = serializers.IntegerField(source='global_quota')
    quota_used = serializers.IntegerField(source='used_quota')
    quota_percentage = serializers.FloatField()
    quota_remaining = serializers.IntegerField(source='remaining_quota')
    max_users = serializers.IntegerField()
    current_users = serializers.IntegerField()
    can_add_user = serializers.BooleanField()


class OrganizationInviteSerializer(serializers.ModelSerializer):
    """Serializer for organization invites"""
    invited_by_email = serializers.EmailField(source='invited_by.email', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    class Meta:
        model = OrganizationInvite
        fields = [
            'id', 'email', 'role', 'token',
            'invited_by', 'invited_by_email',
            'organization', 'organization_name',
            'accepted', 'expires_at', 'created_at'
        ]
        read_only_fields = ['token', 'created_at']


class ExportDataSerializer(serializers.Serializer):
    """Serializer for data export request"""
    include_users = serializers.BooleanField(default=True)
    include_applications = serializers.BooleanField(default=True)
    include_traffic = serializers.BooleanField(default=True)
    include_threats = serializers.BooleanField(default=True)
    include_analytics = serializers.BooleanField(default=True)
    format = serializers.ChoiceField(choices=['json', 'csv'], default='json')
