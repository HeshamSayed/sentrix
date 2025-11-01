from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q
from datetime import timedelta
from .models import MetricSnapshot, Alert, Dashboard
from .serializers import MetricSnapshotSerializer, AlertSerializer, DashboardSerializer

class MetricSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """Metrics and time-series data (read-only)"""
    serializer_class = MetricSnapshotSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['application', 'environment', 'granularity']
    ordering_fields = ['timestamp']
    
    def get_queryset(self):
        user = self.request.user
        if not user.organization:
            return MetricSnapshot.objects.none()
        
        queryset = MetricSnapshot.objects.filter(
            Q(application__organization=user.organization) |
            Q(environment__application__organization=user.organization)
        )
        
        # Filter by environment type (PRODUCTION, STAGING, DEVELOPMENT)
        environment_type = self.request.query_params.get('environment', None)
        if environment_type and environment_type != 'ALL':
            queryset = queryset.filter(environment__type=environment_type)
        
        # Filter by application ID
        application_id = self.request.query_params.get('application_id', None)
        if application_id:
            queryset = queryset.filter(
                Q(application_id=application_id) | Q(environment__application_id=application_id)
            )
        
        # Filter by time range
        time_range = self.request.query_params.get('time_range', '24h')
        now = timezone.now()
        if time_range == '1h':
            start_time = now - timedelta(hours=1)
        elif time_range == '24h':
            start_time = now - timedelta(days=1)
        elif time_range == '7d':
            start_time = now - timedelta(days=7)
        elif time_range == '30d':
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(days=1)
        
        queryset = queryset.filter(timestamp__gte=start_time)
        
        return queryset

class AlertViewSet(viewsets.ModelViewSet):
    """Alert management"""
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['alert_type', 'severity', 'is_acknowledged', 'is_resolved']
    search_fields = ['title', 'message']
    ordering_fields = ['created_at', 'severity']
    
    def get_queryset(self):
        user = self.request.user
        if not user.organization:
            return Alert.objects.none()
        
        queryset = Alert.objects.filter(organization=user.organization)

        # Filter by application ID
        application_id = self.request.query_params.get('application_id', None)
        if application_id:
            queryset = queryset.filter(application_id=application_id)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert"""
        alert = self.get_object()
        alert.is_acknowledged = True
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save()
        return Response(AlertSerializer(alert).data)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an alert"""
        alert = self.get_object()
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save()
        return Response(AlertSerializer(alert).data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get alert summary"""
        queryset = self.get_queryset()
        
        summary = {
            'total': queryset.count(),
            'unresolved': queryset.filter(is_resolved=False).count(),
            'critical': queryset.filter(severity='CRITICAL', is_resolved=False).count(),
            'error': queryset.filter(severity='ERROR', is_resolved=False).count(),
            'warning': queryset.filter(severity='WARNING', is_resolved=False).count(),
            'info': queryset.filter(severity='INFO', is_resolved=False).count(),
        }
        
        return Response(summary)

class DashboardViewSet(viewsets.ModelViewSet):
    """Dashboard management"""
    serializer_class = DashboardSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Dashboard.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        # If this is set as default, unset other defaults
        if serializer.validated_data.get('is_default', False):
            Dashboard.objects.filter(user=self.request.user).update(is_default=False)
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set dashboard as default"""
        # Unset all other defaults
        Dashboard.objects.filter(user=request.user).update(is_default=False)
        # Set this as default
        dashboard = self.get_object()
        dashboard.is_default = True
        dashboard.save()
        return Response(DashboardSerializer(dashboard).data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get overall statistics for dashboard"""
        user = request.user
        if not user.organization:
            return Response({'error': 'No organization found'}, status=status.HTTP_400_BAD_REQUEST)
        
        org = user.organization
        
        # Get filter parameters
        environment_type = request.query_params.get('environment', None)
        application_id = request.query_params.get('application_id', None)
        
        # Get recent metrics
        now = timezone.now()
        last_24h = now - timedelta(days=1)
        
        metrics_filter = Q(application__organization=org) | Q(environment__application__organization=org)
        metrics_filter &= Q(timestamp__gte=last_24h)
        
        # Apply environment filter
        if environment_type and environment_type != 'ALL':
            metrics_filter &= Q(environment__type=environment_type)
        
        # Apply application filter
        if application_id:
            metrics_filter &= (Q(application_id=application_id) | Q(environment__application_id=application_id))
        
        metrics = MetricSnapshot.objects.filter(metrics_filter).aggregate(
            total_requests=Sum('total_requests'),
            failed_requests=Sum('failed_requests'),
            blocked_requests=Sum('blocked_requests'),
            avg_response_time=Avg('avg_response_time_ms'),
            total_threats=Sum('threat_count')
        )
        
        # Filter alerts
        alerts_filter = Q(organization=org, is_resolved=False)
        if application_id:
            alerts_filter &= Q(application_id=application_id)
        
        stats = {
            'organization': {
                'name': org.name,
                'quota_percentage': org.quota_percentage,
                'remaining_quota': org.remaining_quota,
            },
            'applications': {
                'total': org.applications.count(),
                'active': org.applications.filter(is_traffic_enabled=True).count(),
            },
            'users': {
                'total': org.current_users,
                'max': org.max_users,
            },
            'last_24h': {
                'total_requests': metrics['total_requests'] or 0,
                'failed_requests': metrics['failed_requests'] or 0,
                'blocked_requests': metrics['blocked_requests'] or 0,
                'avg_response_time_ms': round(metrics['avg_response_time'] or 0, 2),
                'total_threats': metrics['total_threats'] or 0,
            },
            'alerts': {
                'unresolved': Alert.objects.filter(alerts_filter).count(),
                'critical': Alert.objects.filter(alerts_filter, severity='CRITICAL').count(),
            }
        }
        
        return Response(stats)

