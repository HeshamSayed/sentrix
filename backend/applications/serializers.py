from rest_framework import serializers
from .models import Application, Environment, APIEndpoint, QuotaTransfer

class ApplicationSerializer(serializers.ModelSerializer):
    quota_percentage = serializers.ReadOnlyField()
    remaining_quota = serializers.ReadOnlyField()
    is_quota_exceeded = serializers.ReadOnlyField()
    environments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Application
        fields = [
            'id', 'organization', 'name', 'slug', 'description',
            'allocated_quota', 'used_quota', 'quota_percentage', 'remaining_quota',
            'is_quota_exceeded', 'is_traffic_enabled', 'maintenance_mode',
            'maintenance_message', 'blocked_countries', 'allowed_countries',
            'blocked_ips', 'allowed_ips', 'settings', 'environments_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organization', 'used_quota', 'created_at', 'updated_at']
    
    def get_environments_count(self, obj):
        return obj.environments.count()

class EnvironmentSerializer(serializers.ModelSerializer):
    application_name = serializers.CharField(source='application.name', read_only=True)
    endpoints_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Environment
        fields = [
            'id', 'application', 'application_name', 'name', 'base_domain',
            'is_active', 'maintenance_mode', 'maintenance_message', 
            'resources', 'api_endpoints', 'settings',
            'endpoints_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_endpoints_count(self, obj):
        return obj.discovered_endpoints.count()

class APIEndpointSerializer(serializers.ModelSerializer):
    environment_name = serializers.CharField(source='environment.name', read_only=True)
    error_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = APIEndpoint
        fields = [
            'id', 'environment', 'environment_name', 'method', 'path',
            'path_pattern', 'first_seen', 'last_seen', 'request_count',
            'error_count', 'error_rate', 'is_sensitive', 'risk_score',
            'security_issues', 'created_at'
        ]
        read_only_fields = ['id', 'first_seen', 'last_seen', 'created_at']
    
    def get_error_rate(self, obj):
        if obj.request_count == 0:
            return 0
        return (obj.error_count / obj.request_count) * 100

class QuotaTransferSerializer(serializers.ModelSerializer):
    from_application_name = serializers.CharField(source='from_application.name', read_only=True, allow_null=True)
    to_application_name = serializers.CharField(source='to_application.name', read_only=True)
    performed_by_email = serializers.CharField(source='performed_by.email', read_only=True)
    
    class Meta:
        model = QuotaTransfer
        fields = [
            'id', 'organization', 'from_application', 'from_application_name',
            'to_application', 'to_application_name', 'amount', 'reason',
            'performed_by', 'performed_by_email', 'created_at'
        ]
        read_only_fields = ['id', 'organization', 'performed_by', 'created_at']

