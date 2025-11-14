"""
Detection API views.
"""
import logging
from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import DetectionEvent
from .serializers import (
    DetectionEventSerializer,
    DetectionEventCreateSerializer,
    DetectionEventUpdateSerializer,
    DetectionSummarySerializer,
)

logger = logging.getLogger(__name__)


class DetectionEventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing detection events.

    list: Get all detections (filtered by user's org and optionally app)
    retrieve: Get a specific detection
    create: Create a new detection (typically from consumers)
    update: Update detection status
    partial_update: Partially update detection
    """
    queryset = DetectionEvent.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return DetectionEventCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return DetectionEventUpdateSerializer
        return DetectionEventSerializer

    def get_queryset(self):
        """
        Filter by authenticated user's org and optionally by app.

        Query params:
            app_id: Filter by specific application
            severity: Filter by severity (info, low, medium, high, critical)
            status: Filter by status (open, investigating, confirmed, false_positive, resolved)
            detector_type: Filter by detector type
            attack_type: Filter by attack type
        """
        user = self.request.user
        queryset = DetectionEvent.objects.filter(org_id=user.org_id).select_related(
            'org', 'app', 'endpoint', 'assigned_to'
        )

        # Filter by app if specified
        app_id = self.request.query_params.get('app_id')
        if app_id:
            queryset = queryset.filter(app_id=app_id)

        # Filter by severity
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by detector type
        detector_type = self.request.query_params.get('detector_type')
        if detector_type:
            queryset = queryset.filter(detector_type=detector_type)

        # Filter by attack type
        attack_type = self.request.query_params.get('attack_type')
        if attack_type:
            queryset = queryset.filter(attack_type=attack_type)

        return queryset.order_by('-detected_at')

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get detection summary statistics.

        GET /api/detections/summary/?app_id={app_id}

        Returns:
        {
            "total": 1234,
            "open": 45,
            "investigating": 12,
            "confirmed": 8,
            "false_positive": 15,
            "resolved": 1154,
            "by_severity": {...},
            "by_detector_type": {...},
            "recent_detections": [...]
        }
        """
        user = request.user
        queryset = DetectionEvent.objects.filter(org_id=user.org_id)

        # Filter by app if specified
        app_id = request.query_params.get('app_id')
        if app_id:
            queryset = queryset.filter(app_id=app_id)

        # Count by status
        total = queryset.count()
        status_counts = queryset.values('status').annotate(count=Count('status'))
        status_dict = {item['status']: item['count'] for item in status_counts}

        # Count by severity
        severity_counts = queryset.values('severity').annotate(count=Count('severity'))
        severity_dict = {item['severity']: item['count'] for item in severity_counts}

        # Count by detector type
        detector_counts = queryset.values('detector_type').annotate(count=Count('detector_type'))
        detector_dict = {item['detector_type']: item['count'] for item in detector_counts}

        # Recent detections (last 10)
        recent = queryset.select_related('org', 'app', 'endpoint', 'assigned_to').order_by('-detected_at')[:10]
        recent_serializer = DetectionEventSerializer(recent, many=True)

        summary = {
            'total': total,
            'open': status_dict.get('open', 0),
            'investigating': status_dict.get('investigating', 0),
            'confirmed': status_dict.get('confirmed', 0),
            'false_positive': status_dict.get('false_positive', 0),
            'resolved': status_dict.get('resolved', 0),
            'by_severity': severity_dict,
            'by_detector_type': detector_dict,
            'recent_detections': recent_serializer.data
        }

        return Response(summary)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """
        Assign detection to a user.

        POST /api/detections/{detection_id}/assign/
        {
            "assigned_to": "user_id"
        }
        """
        detection = self.get_object()
        user_id = request.data.get('assigned_to')

        if not user_id:
            return Response(
                {'error': 'assigned_to is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify user exists and is in same org
        from core.models import User
        try:
            user = User.objects.get(user_id=user_id, org_id=detection.org_id, is_active=True)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found or not in same organization'},
                status=status.HTTP_404_NOT_FOUND
            )

        detection.assigned_to = user
        if detection.status == 'open':
            detection.status = 'investigating'
        detection.save()

        serializer = self.get_serializer(detection)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """
        Close a detection (mark as resolved or false positive).

        POST /api/detections/{detection_id}/close/
        {
            "status": "resolved" or "false_positive",
            "notes": "Optional notes"
        }
        """
        detection = self.get_object()
        new_status = request.data.get('status')

        if new_status not in ['resolved', 'false_positive']:
            return Response(
                {'error': 'status must be "resolved" or "false_positive"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        detection.status = new_status
        detection.save()

        # TODO: Log audit event

        serializer = self.get_serializer(detection)
        return Response(serializer.data)
