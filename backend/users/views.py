from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import User, APIKey, AuditLog
from .serializers import UserSerializer, UserCreateSerializer, APIKeySerializer, AuditLogSerializer
from core.permissions import CanManageUsers
import secrets

class UserViewSet(viewsets.ModelViewSet):
    """User management viewset"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return User.objects.all()
        if user.organization:
            return User.objects.filter(organization=user.organization)
        return User.objects.none()
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageUsers()]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        user = serializer.save(organization=self.request.user.organization)
        # Increment organization user count
        if user.organization:
            user.organization.current_users += 1
            user.organization.save()
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanManageUsers])
    def disable(self, request, pk=None):
        """Disable a user"""
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'status': 'User disabled'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanManageUsers])
    def enable(self, request, pk=None):
        """Enable a user"""
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({'status': 'User enabled'})
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user info"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

class APIKeyViewSet(viewsets.ModelViewSet):
    """API Key management"""
    serializer_class = APIKeySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        # Generate secure API key
        key = f"sk_{secrets.token_urlsafe(32)}"
        serializer.save(user=self.request.user, key=key)

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Audit log viewset (read-only)"""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['action', 'resource_type']
    search_fields = ['action', 'resource_type', 'user__email']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_root:
            return AuditLog.objects.filter(organization=user.organization)
        return AuditLog.objects.filter(user=user)

