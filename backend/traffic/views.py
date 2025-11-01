from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import APIRequest, ThreatDetection, BlockedIP, RateLimitRule
from .serializers import (
    APIRequestSerializer, ThreatDetectionSerializer,
    BlockedIPSerializer, RateLimitRuleSerializer
)
from core.permissions import IsAdminUser

class APIRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """API Request logs (read-only)"""
    serializer_class = APIRequestSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['environment', 'method', 'status_code', 'is_blocked']
    search_fields = ['path', 'ip_address']
    ordering_fields = ['timestamp', 'response_time_ms', 'threat_score']
    
    def get_queryset(self):
        user = self.request.user
        if not user.organization:
            return APIRequest.objects.none()
        
        queryset = APIRequest.objects.filter(
            environment__application__organization=user.organization
        )
        
        # Filter by environment type (PRODUCTION, STAGING, DEVELOPMENT)
        environment_type = self.request.query_params.get('environment', None)
        if environment_type and environment_type != 'ALL':
            queryset = queryset.filter(environment__type=environment_type)
        
        # Filter by application ID
        application_id = self.request.query_params.get('application_id', None)
        if application_id:
            queryset = queryset.filter(environment__application_id=application_id)
        
        return queryset

class ThreatDetectionViewSet(viewsets.ModelViewSet):
    """Threat detection management"""
    serializer_class = ThreatDetectionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['environment', 'severity', 'status', 'threat_type']
    search_fields = ['title', 'description', 'ip_address']
    ordering_fields = ['created_at', 'severity']
    
    def get_queryset(self):
        user = self.request.user
        if not user.organization:
            return ThreatDetection.objects.none()
        
        queryset = ThreatDetection.objects.filter(
            environment__application__organization=user.organization
        )
        
        # Filter by environment type (PRODUCTION, STAGING, DEVELOPMENT)
        environment_type = self.request.query_params.get('environment', None)
        if environment_type and environment_type != 'ALL':
            queryset = queryset.filter(environment__type=environment_type)
        
        # Filter by application ID
        application_id = self.request.query_params.get('application_id', None)
        if application_id:
            queryset = queryset.filter(environment__application_id=application_id)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a threat"""
        threat = self.get_object()
        threat.status = 'RESOLVED'
        threat.resolved_at = timezone.now()
        threat.resolved_by = request.user
        threat.resolution_notes = request.data.get('notes', '')
        threat.save()
        return Response(ThreatDetectionSerializer(threat).data)
    
    @action(detail=True, methods=['post'])
    def mark_false_positive(self, request, pk=None):
        """Mark threat as false positive"""
        threat = self.get_object()
        threat.status = 'FALSE_POSITIVE'
        threat.resolved_at = timezone.now()
        threat.resolved_by = request.user
        threat.resolution_notes = request.data.get('notes', '')
        threat.save()
        return Response(ThreatDetectionSerializer(threat).data)

class BlockedIPViewSet(viewsets.ModelViewSet):
    """Blocked IP management"""
    serializer_class = BlockedIPSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filterset_fields = ['application']
    search_fields = ['ip_address', 'reason']
    
    def get_queryset(self):
        user = self.request.user
        if user.organization:
            return BlockedIP.objects.filter(organization=user.organization)
        return BlockedIP.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            blocked_by=self.request.user
        )

class RateLimitRuleViewSet(viewsets.ModelViewSet):
    """Rate limit rule management"""
    serializer_class = RateLimitRuleSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filterset_fields = ['application', 'is_active']
    search_fields = ['name', 'path_pattern']
    
    def get_queryset(self):
        user = self.request.user
        if user.organization:
            return RateLimitRule.objects.filter(
                application__organization=user.organization
            )
        return RateLimitRule.objects.none()
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Enable/disable rate limit rule"""
        rule = self.get_object()
        rule.is_active = not rule.is_active
        rule.save()
        return Response({
            'status': 'Rule enabled' if rule.is_active else 'Rule disabled'
        })

