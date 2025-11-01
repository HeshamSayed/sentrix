from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from .models import (
    AnomalyDetection,
    ThreatResponse,
    BlockedEntity,
    SecurityConfiguration,
    UserBehaviorBaseline,
    APIBehaviorLog
)
from .serializers import (
    AnomalyDetectionSerializer,
    ThreatResponseSerializer,
    BlockedEntitySerializer,
    SecurityConfigurationSerializer,
    UserBehaviorBaselineSerializer,
    APIBehaviorLogSerializer,
    SecurityStatsSerializer
)


class AnomalyDetectionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing detected anomalies"""
    serializer_class = AnomalyDetectionSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filterset_fields = ['severity', 'status', 'anomaly_type', 'user']
    search_fields = ['title', 'description', 'ip_address']
    ordering_fields = ['timestamp', 'risk_score', 'severity']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        return AnomalyDetection.objects.select_related('user').all()
    
    @action(detail=True, methods=['post'])
    def mark_false_positive(self, request, pk=None):
        """Mark an anomaly as false positive"""
        anomaly = self.get_object()
        anomaly.status = 'FALSE_POSITIVE'
        anomaly.investigated_by = request.user
        anomaly.investigated_at = timezone.now()
        anomaly.notes = request.data.get('notes', '')
        anomaly.save()
        
        return Response({
            'status': 'Marked as false positive',
            'anomaly': self.get_serializer(anomaly).data
        })
    
    @action(detail=True, methods=['post'])
    def confirm_threat(self, request, pk=None):
        """Confirm an anomaly as real threat"""
        anomaly = self.get_object()
        anomaly.status = 'CONFIRMED'
        anomaly.investigated_by = request.user
        anomaly.investigated_at = timezone.now()
        anomaly.notes = request.data.get('notes', '')
        anomaly.save()
        
        return Response({
            'status': 'Confirmed as threat',
            'anomaly': self.get_serializer(anomaly).data
        })


class BlockedEntityViewSet(viewsets.ModelViewSet):
    """ViewSet for managing blocked entities"""
    serializer_class = BlockedEntitySerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filterset_fields = ['entity_type', 'is_permanent']
    search_fields = ['entity_value', 'reason']
    ordering = ['-blocked_at']
    
    def get_queryset(self):
        return BlockedEntity.objects.all()
    
    def perform_create(self, serializer):
        serializer.save(blocked_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        """Unblock an entity"""
        entity = self.get_object()
        entity.unblocked_at = timezone.now()
        entity.unblocked_by = request.user
        entity.save()
        
        return Response({
            'status': 'Entity unblocked',
            'entity': self.get_serializer(entity).data
        })


class SecurityConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for security configuration"""
    serializer_class = SecurityConfigurationSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        return SecurityConfiguration.objects.all()
    
    def perform_update(self, serializer):
        serializer.save(last_updated_by=self.request.user)


class SecurityDashboardViewSet(viewsets.ViewSet):
    """ViewSet for security dashboard statistics"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get security statistics"""
        today = timezone.now().date()
        
        # Get statistics
        stats = {
            'total_requests_today': APIBehaviorLog.objects.filter(
                timestamp__date=today
            ).count(),
            'anomalies_today': AnomalyDetection.objects.filter(
                timestamp__date=today
            ).count(),
            'critical_threats': AnomalyDetection.objects.filter(
                severity='CRITICAL',
                status__in=['DETECTED', 'INVESTIGATING', 'CONFIRMED']
            ).count(),
            'blocked_entities': BlockedEntity.objects.filter(
                Q(is_permanent=True, unblocked_at__isnull=True) |
                Q(blocked_until__gt=timezone.now(), unblocked_at__isnull=True)
            ).count(),
            'top_threats': AnomalyDetection.objects.filter(
                timestamp__gte=timezone.now() - timedelta(days=7),
                severity__in=['HIGH', 'CRITICAL']
            ).order_by('-risk_score')[:5],
            'recent_blocks': BlockedEntity.objects.order_by('-blocked_at')[:5]
        }
        
        serializer = SecurityStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def timeline(self, request):
        """Get anomaly timeline"""
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        
        timeline = AnomalyDetection.objects.filter(
            timestamp__gte=start_date
        ).extra(
            select={'day': 'date(timestamp)'}
        ).values('day', 'severity').annotate(
            count=Count('id')
        ).order_by('day', 'severity')
        
        return Response(list(timeline))
    
    @action(detail=False, methods=['get'])
    def top_attackers(self, request):
        """Get top attacking IPs"""
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        
        attackers = AnomalyDetection.objects.filter(
            timestamp__gte=start_date
        ).values('ip_address').annotate(
            attack_count=Count('id'),
            max_risk=Max('risk_score')
        ).order_by('-attack_count')[:10]
        
        return Response(list(attackers))
    
    @action(detail=False, methods=['get'])
    def attack_types(self, request):
        """Get distribution of attack types"""
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        
        attack_types = AnomalyDetection.objects.filter(
            timestamp__gte=start_date
        ).values('anomaly_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return Response(list(attack_types))


class UserBehaviorBaselineViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing user behavior baselines"""
    serializer_class = UserBehaviorBaselineSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filterset_fields = ['user', 'endpoint']
    ordering = ['-last_calculated']
    
    def get_queryset(self):
        return UserBehaviorBaseline.objects.select_related('user').all()


# Import for aggregation
from django.db.models import Max

