"""
DRF serializers for detection models.
"""
from rest_framework import serializers
from .models import DetectionEvent
from core.models import APIEndpoint, User


class DetectionEventSerializer(serializers.ModelSerializer):
    """Detection event serializer"""

    org_name = serializers.CharField(source='org.name', read_only=True)
    app_name = serializers.CharField(source='app.name', read_only=True)
    endpoint_path = serializers.SerializerMethodField()
    assigned_to_email = serializers.CharField(source='assigned_to.email', read_only=True, allow_null=True)

    class Meta:
        model = DetectionEvent
        fields = [
            'detection_id',
            'org',
            'org_name',
            'app',
            'app_name',
            'endpoint',
            'endpoint_path',
            'trigger_event_ids',
            'trace_ids',
            'detector_type',
            'detector_name',
            'severity',
            'confidence_score',
            'r1_score',
            'r1_explanation',
            'attack_type',
            'client_ip',
            'status',
            'assigned_to',
            'assigned_to_email',
            'detected_at',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'detection_id',
            'detected_at',
            'created_at',
            'updated_at'
        ]

    def get_endpoint_path(self, obj):
        """Get endpoint path pattern"""
        if obj.endpoint:
            return f"{obj.endpoint.method} {obj.endpoint.path_pattern}"
        return None


class DetectionEventCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating detections (from consumers)"""

    class Meta:
        model = DetectionEvent
        fields = [
            'org',
            'app',
            'endpoint',
            'trigger_event_ids',
            'trace_ids',
            'detector_type',
            'detector_name',
            'severity',
            'confidence_score',
            'r1_score',
            'r1_explanation',
            'attack_type',
            'client_ip'
        ]


class DetectionEventUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating detection status"""

    class Meta:
        model = DetectionEvent
        fields = ['status', 'assigned_to']


class DetectionSummarySerializer(serializers.Serializer):
    """Serializer for detection summary stats"""

    total = serializers.IntegerField()
    open = serializers.IntegerField()
    investigating = serializers.IntegerField()
    confirmed = serializers.IntegerField()
    false_positive = serializers.IntegerField()
    resolved = serializers.IntegerField()
    by_severity = serializers.DictField()
    by_detector_type = serializers.DictField()
    recent_detections = DetectionEventSerializer(many=True)
