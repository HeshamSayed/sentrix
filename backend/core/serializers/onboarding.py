"""
Onboarding serializers for Organization → Environment → Application hierarchy
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from core.models import SubscriptionPlan, Subscription, OnboardingSession
from applications.models import Environment, Application
from organizations.models import Organization

User = get_user_model()


class SignUpSerializer(serializers.Serializer):
    """User registration"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    company_name = serializers.CharField(max_length=255)
    company_size = serializers.CharField(max_length=50, required=False)
    use_case = serializers.CharField(required=False)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Subscription plan details"""
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'plan_type', 'description',
            'monthly_price', 'annual_price',
            'max_requests_per_month', 'max_applications', 'max_users', 'max_environments',
            'behavioral_analysis', 'real_time_blocking', 'advanced_analytics',
            'custom_rules', 'priority_support', 'dedicated_resources', 'sla_guarantee'
        ]


class ApplicationCreateSerializer(serializers.Serializer):
    """Create application under an environment"""
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    base_url = serializers.URLField()
    target_url = serializers.URLField()
    allocated_quota = serializers.IntegerField(required=False, allow_null=True, help_text="Optional: Quota for this application. Leave blank to configure later in dashboard.")
    rate_limit_per_minute = serializers.IntegerField(required=False, allow_null=True)
    rate_limit_per_hour = serializers.IntegerField(required=False, allow_null=True)
    rate_limit_per_day = serializers.IntegerField(required=False, allow_null=True)
    framework = serializers.CharField(max_length=100, required=False, allow_blank=True)
    language = serializers.CharField(max_length=50, required=False, allow_blank=True)


class EnvironmentCreateSerializer(serializers.Serializer):
    """Create environment with applications"""
    name = serializers.CharField(max_length=100)
    environment_type = serializers.ChoiceField(
        choices=['development', 'staging', 'production', 'testing', 'custom'],
        default='production'
    )
    description = serializers.CharField(required=False, allow_blank=True)
    allocated_quota = serializers.IntegerField(required=False, allow_null=True, help_text="Optional: Quota for this environment. Leave blank to configure later in dashboard.")
    applications = ApplicationCreateSerializer(many=True)


class QuickStartSerializer(serializers.Serializer):
    """
    Quick start onboarding - creates organization, subscription, and environment with applications
    
    Example:
    {
        "organization_name": "TODO App Inc",
        "plan_type": "starter",
        "environments": [
            {
                "name": "Production",
                "environment_type": "production",
                "applications": [
                    {
                        "name": "TODO App API",
                        "base_url": "https://todo.com",
                        "target_url": "https://api.todo.com",
                        "framework": "Flask",
                        "language": "Python"
                    }
                ]
            },
            {
                "name": "Staging",
                "environment_type": "staging",
                "applications": [
                    {
                        "name": "TODO App API Staging",
                        "base_url": "https://staging.todo.com",
                        "target_url": "https://api-staging.todo.com"
                    }
                ]
            }
        ]
    }
    """
    organization_name = serializers.CharField(max_length=255)
    plan_type = serializers.ChoiceField(
        choices=['free', 'starter', 'professional', 'enterprise'],
        default='starter'
    )
    environments = EnvironmentCreateSerializer(many=True)


class OnboardingSerializer(serializers.ModelSerializer):
    """Onboarding session"""
    class Meta:
        model = OnboardingSession
        fields = ['id', 'status', 'company_name', 'company_size', 'use_case', 'completed_at']


class EnvironmentDetailSerializer(serializers.ModelSerializer):
    """Environment details"""
    total_applications = serializers.IntegerField(read_only=True)
    active_applications = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Environment
        fields = [
            'id', 'name', 'environment_type', 'slug', 'description',
            'is_active', 'maintenance_mode', 'max_applications', 'allocated_quota',
            'total_applications', 'active_applications', 'created_at', 'updated_at'
        ]


class ApplicationDetailSerializer(serializers.ModelSerializer):
    """Application details with API key"""
    organization_name = serializers.CharField(source='environment.organization.name', read_only=True)
    environment_name = serializers.CharField(source='environment.name', read_only=True)
    quota_percentage = serializers.FloatField(read_only=True)
    remaining_quota = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Application
        fields = [
            'id', 'name', 'slug', 'description', 'api_key',
            'base_url', 'target_url', 'is_active', 'is_traffic_enabled',
            'allocated_quota', 'used_quota', 'quota_percentage', 'remaining_quota',
            'rate_limit_per_minute', 'rate_limit_per_hour', 'rate_limit_per_day',
            'framework', 'language', 'organization_name', 'environment_name',
            'created_at', 'updated_at'
        ]


class QuickStartResponseSerializer(serializers.Serializer):
    """Response for quick start"""
    organization = serializers.DictField()
    subscription = serializers.DictField()
    environments = EnvironmentDetailSerializer(many=True)
    applications = ApplicationDetailSerializer(many=True)
    message = serializers.CharField()
    next_steps = serializers.ListField(child=serializers.CharField())
