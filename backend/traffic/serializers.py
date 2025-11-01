from rest_framework import serializers
from .models import APIRequest, ThreatDetection, BlockedIP, RateLimitRule

class APIRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIRequest
        fields = [
            'id', 'environment', 'method', 'path', 'query_params',
            'ip_address', 'user_agent', 'country_code', 'status_code',
            'response_time_ms', 'is_blocked', 'block_reason',
            'threat_score', 'threat_indicators', 'request_id',
            'timestamp', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class ThreatDetectionSerializer(serializers.ModelSerializer):
    resolved_by_email = serializers.CharField(source='resolved_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = ThreatDetection
        fields = [
            'id', 'environment', 'threat_type', 'severity', 'status',
            'title', 'description', 'ip_address', 'affected_endpoint',
            'evidence', 'resolved_at', 'resolved_by', 'resolved_by_email',
            'resolution_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class BlockedIPSerializer(serializers.ModelSerializer):
    blocked_by_email = serializers.CharField(source='blocked_by.email', read_only=True, allow_null=True)
    application_name = serializers.CharField(source='application.name', read_only=True, allow_null=True)
    
    class Meta:
        model = BlockedIP
        fields = [
            'id', 'organization', 'ip_address', 'reason', 'application',
            'application_name', 'expires_at', 'blocked_by', 'blocked_by_email',
            'created_at'
        ]
        read_only_fields = ['id', 'organization', 'blocked_by', 'created_at']

class RateLimitRuleSerializer(serializers.ModelSerializer):
    application_name = serializers.CharField(source='application.name', read_only=True)
    
    class Meta:
        model = RateLimitRule
        fields = [
            'id', 'application', 'application_name', 'name', 'description',
            'path_pattern', 'max_requests', 'time_window_seconds',
            'applies_to', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

