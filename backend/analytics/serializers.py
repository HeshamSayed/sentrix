from rest_framework import serializers
from .models import MetricSnapshot, Alert, Dashboard

class MetricSnapshotSerializer(serializers.ModelSerializer):
    application_name = serializers.CharField(source='application.name', read_only=True, allow_null=True)
    environment_name = serializers.CharField(source='environment.name', read_only=True, allow_null=True)
    
    class Meta:
        model = MetricSnapshot
        fields = [
            'id', 'application', 'application_name', 'environment', 'environment_name',
            'timestamp', 'granularity', 'total_requests', 'successful_requests',
            'failed_requests', 'blocked_requests', 'avg_response_time_ms',
            'p95_response_time_ms', 'p99_response_time_ms', 'threat_count',
            'high_risk_requests', 'unique_ips', 'unique_endpoints',
            'bytes_sent', 'bytes_received', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class AlertSerializer(serializers.ModelSerializer):
    acknowledged_by_email = serializers.CharField(source='acknowledged_by.email', read_only=True, allow_null=True)
    application_name = serializers.CharField(source='application.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Alert
        fields = [
            'id', 'organization', 'application', 'application_name',
            'alert_type', 'severity', 'title', 'message', 'data',
            'is_acknowledged', 'acknowledged_by', 'acknowledged_by_email',
            'acknowledged_at', 'is_resolved', 'resolved_at', 'created_at'
        ]
        read_only_fields = ['id', 'organization', 'created_at']

class DashboardSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Dashboard
        fields = [
            'id', 'user', 'user_email', 'name', 'description',
            'layout', 'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

