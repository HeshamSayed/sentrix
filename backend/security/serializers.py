from rest_framework import serializers
from .models import (
    AnomalyDetection,
    ThreatResponse,
    BlockedEntity,
    SecurityConfiguration,
    UserBehaviorBaseline,
    APIBehaviorLog
)


class APIBehaviorLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = APIBehaviorLog
        fields = [
            'id', 'user', 'user_email', 'session_id', 'ip_address',
            'user_agent', 'method', 'endpoint', 'status_code',
            'response_time_ms', 'timestamp', 'geo_country'
        ]


class AnomalyDetectionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    responses = serializers.SerializerMethodField()
    
    class Meta:
        model = AnomalyDetection
        fields = [
            'id', 'user', 'user_email', 'anomaly_type', 'severity',
            'confidence_score', 'risk_score', 'title', 'description',
            'indicators', 'ip_address', 'endpoint', 'timestamp',
            'status', 'responses', 'created_at'
        ]
    
    def get_responses(self, obj):
        responses = obj.threatresponse_set.all()
        return ThreatResponseSerializer(responses, many=True).data


class ThreatResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThreatResponse
        fields = [
            'id', 'action_taken', 'duration_minutes', 'parameters',
            'success', 'error_message', 'executed_at'
        ]


class BlockedEntitySerializer(serializers.ModelSerializer):
    blocked_by_email = serializers.EmailField(source='blocked_by.email', read_only=True)
    is_active = serializers.SerializerMethodField()
    
    class Meta:
        model = BlockedEntity
        fields = [
            'id', 'entity_type', 'entity_value', 'reason',
            'blocked_at', 'blocked_until', 'is_permanent',
            'blocked_by', 'blocked_by_email', 'is_active',
            'unblocked_at', 'created_at'
        ]
    
    def get_is_active(self, obj):
        from django.utils import timezone
        if obj.is_permanent:
            return not obj.unblocked_at
        if obj.blocked_until:
            return timezone.now() < obj.blocked_until and not obj.unblocked_at
        return False


class SecurityConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityConfiguration
        fields = [
            'id', 'velocity_threshold_multiplier', 'anomaly_score_threshold',
            'min_requests_for_baseline', 'baseline_window_days',
            'auto_block_enabled', 'auto_rate_limit_enabled',
            'block_duration_minutes', 'alert_on_severity', 'alert_channels',
            'model_update_frequency_minutes', 'is_active', 'updated_at'
        ]


class UserBehaviorBaselineSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = UserBehaviorBaseline
        fields = [
            'id', 'user', 'user_email', 'endpoint',
            'avg_requests_per_hour', 'avg_requests_per_day',
            'avg_response_time_ms', 'common_endpoints',
            'typical_hours', 'samples_count', 'last_calculated'
        ]


class SecurityStatsSerializer(serializers.Serializer):
    """Serializer for security statistics"""
    total_requests_today = serializers.IntegerField()
    anomalies_today = serializers.IntegerField()
    critical_threats = serializers.IntegerField()
    blocked_entities = serializers.IntegerField()
    top_threats = AnomalyDetectionSerializer(many=True)
    recent_blocks = BlockedEntitySerializer(many=True)

