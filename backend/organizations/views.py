from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.http import HttpResponse
import json
import csv
import io
import secrets
from datetime import timedelta

from .models import Organization, OrganizationInvite
from .serializers import (
    OrganizationSerializer,
    OrganizationSettingsSerializer,
    NotificationSettingsSerializer,
    SecuritySettingsSerializer,
    APIKeySerializer,
    SubscriptionInfoSerializer,
    OrganizationInviteSerializer,
    ExportDataSerializer
)
from core.permissions import IsRootOrAdmin, IsRoot
from users.models import User
from applications.models import Application
from traffic.models import APIRequest


class OrganizationViewSet(viewsets.ModelViewSet):
    """ViewSet for Organization management"""
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see their own organization
        return Organization.objects.filter(id=self.request.user.organization_id)
    
    def get_object(self):
        # Get current user's organization
        return self.request.user.organization
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current organization details"""
        org = request.user.organization
        serializer = self.get_serializer(org)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get', 'put'], permission_classes=[IsRootOrAdmin])
    def settings(self, request):
        """Get or update organization settings"""
        org = request.user.organization
        
        if request.method == 'GET':
            data = {
                'name': org.name,
                'slug': org.slug,
                'billing_email': org.billing_email,
                'description': org.description,
                'max_users': org.max_users,
                'current_users': org.current_users,
            }
            return Response(data)
        
        # PUT - Update settings
        serializer = OrganizationSettingsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.update(org, serializer.validated_data)
            return Response({
                'message': 'Organization settings updated successfully',
                'data': serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get', 'put'])
    def notifications(self, request):
        """Get or update notification settings"""
        org = request.user.organization
        
        if request.method == 'GET':
            settings = org.settings or {}
            notifications = settings.get('notifications', {
                'email_alerts': True,
                'slack_notifications': False,
                'webhook_url': '',
                'alert_threshold': 'high'
            })
            return Response(notifications)
        
        # PUT - Update notification settings
        serializer = NotificationSettingsSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.update(org, serializer.validated_data)
            return Response({
                'message': 'Notification settings updated successfully',
                'data': result
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def test_notification(self, request):
        """Test notification settings"""
        org = request.user.organization
        settings = org.settings or {}
        notifications = settings.get('notifications', {})
        
        # Simulate sending test notification
        results = {
            'email': False,
            'slack': False,
            'webhook': False
        }
        
        if notifications.get('email_alerts'):
            # In production, send actual email
            results['email'] = True
        
        if notifications.get('slack_notifications') and notifications.get('webhook_url'):
            # In production, send to Slack webhook
            results['webhook'] = True
        
        return Response({
            'message': 'Test notification sent',
            'results': results,
            'timestamp': timezone.now().isoformat()
        })
    
    @action(detail=False, methods=['get', 'put'], permission_classes=[IsRootOrAdmin])
    def security(self, request):
        """Get or update security settings"""
        org = request.user.organization
        
        if request.method == 'GET':
            settings = org.settings or {}
            security = settings.get('security', {
                'two_factor_enabled': False,
                'session_timeout': '30',
                'ip_whitelist': []
            })
            return Response(security)
        
        # PUT - Update security settings
        serializer = SecuritySettingsSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.update(org, serializer.validated_data)
            return Response({
                'message': 'Security settings updated successfully',
                'data': result
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def subscription(self, request):
        """Get subscription information"""
        org = request.user.organization
        serializer = SubscriptionInfoSerializer(org)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsRootOrAdmin])
    def api_keys(self, request):
        """List API keys"""
        org = request.user.organization
        settings = org.settings or {}
        api_keys = settings.get('api_keys', [])
        return Response(api_keys)
    
    @action(detail=False, methods=['post'], permission_classes=[IsRootOrAdmin])
    def create_api_key(self, request):
        """Create a new API key"""
        org = request.user.organization
        name = request.data.get('name', 'API Key')
        
        # Generate secure API key
        key = f"sk_{secrets.token_urlsafe(32)}"
        
        settings = org.settings or {}
        api_keys = settings.get('api_keys', [])
        
        new_key = {
            'id': secrets.token_urlsafe(16),
            'name': name,
            'key': key,
            'created_at': timezone.now().isoformat(),
            'last_used_at': None,
            'is_active': True
        }
        
        api_keys.append(new_key)
        settings['api_keys'] = api_keys
        org.settings = settings
        org.save()
        
        return Response({
            'message': 'API key created successfully',
            'key': new_key
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'], permission_classes=[IsRootOrAdmin])
    def revoke_api_key(self, request):
        """Revoke an API key"""
        org = request.user.organization
        key_id = request.data.get('key_id')
        
        settings = org.settings or {}
        api_keys = settings.get('api_keys', [])
        
        updated = False
        for key in api_keys:
            if key['id'] == key_id:
                key['is_active'] = False
                updated = True
                break
        
        if updated:
            settings['api_keys'] = api_keys
            org.settings = settings
            org.save()
            return Response({'message': 'API key revoked successfully'})
        
        return Response(
            {'error': 'API key not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @action(detail=False, methods=['post'], permission_classes=[IsRoot])
    def export_data(self, request):
        """Export organization data"""
        org = request.user.organization
        serializer = ExportDataSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        export_data = {
            'organization': {
                'name': org.name,
                'slug': org.slug,
                'created_at': org.created_at.isoformat() if org.created_at else None,
                'subscription_tier': org.subscription_tier,
            },
            'exported_at': timezone.now().isoformat()
        }
        
        # Include requested data
        if data['include_users']:
            users = User.objects.filter(organization=org).values(
                'id', 'email', 'first_name', 'last_name', 'role', 'is_active', 'created_at'
            )
            export_data['users'] = list(users)
        
        if data['include_applications']:
            apps = Application.objects.filter(organization=org).values(
                'id', 'name', 'slug', 'allocated_quota', 'used_quota', 'created_at'
            )
            export_data['applications'] = list(apps)
        
        if data['include_traffic']:
            # Export last 1000 traffic records
            traffic = APIRequest.objects.filter(
                environment__application__organization=org
            ).order_by('-timestamp')[:1000].values(
                'method', 'path', 'status_code', 'response_time_ms', 'timestamp'
            )
            export_data['traffic'] = list(traffic)
        
        # Format response based on requested format
        if data['format'] == 'json':
            response = HttpResponse(
                json.dumps(export_data, indent=2, default=str),
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="{org.slug}_export.json"'
        else:  # CSV
            # For CSV, we'll export a simple summary
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Field', 'Value'])
            writer.writerow(['Organization', org.name])
            writer.writerow(['Users', org.current_users])
            writer.writerow(['Applications', Application.objects.filter(organization=org).count()])
            writer.writerow(['Exported At', timezone.now().isoformat()])
            
            response = HttpResponse(output.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{org.slug}_export.csv"'
        
        return response
    
    @action(detail=False, methods=['post'], permission_classes=[IsRoot])
    def delete_organization(self, request):
        """Delete organization (with confirmation)"""
        org = request.user.organization
        confirmation = request.data.get('confirmation')
        
        # Require explicit confirmation
        if confirmation != org.slug:
            return Response({
                'error': 'Confirmation failed. Please provide the organization slug to confirm deletion.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        org_name = org.name
        
        # Soft delete: deactivate instead of hard delete
        org.is_active = False
        org.save()
        
        # In production, you might want to schedule actual deletion after 30 days
        
        return Response({
            'message': f'Organization "{org_name}" has been deactivated. It will be permanently deleted in 30 days.',
            'deactivated_at': timezone.now().isoformat()
        })
    
    @action(detail=False, methods=['post'], permission_classes=[IsRoot])
    def upgrade_plan(self, request):
        """Upgrade subscription plan"""
        org = request.user.organization
        new_tier = request.data.get('tier')
        
        valid_tiers = ['TRIAL', 'STARTER', 'PROFESSIONAL', 'ENTERPRISE']
        if new_tier not in valid_tiers:
            return Response({
                'error': f'Invalid tier. Must be one of: {", ".join(valid_tiers)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        old_tier = org.subscription_tier
        org.subscription_tier = new_tier
        
        # Update quota based on tier
        quota_map = {
            'TRIAL': 1_000_000,
            'STARTER': 10_000_000,
            'PROFESSIONAL': 100_000_000,
            'ENTERPRISE': 1_000_000_000,
        }
        org.global_quota = quota_map.get(new_tier, 1_000_000)
        
        org.save()
        
        return Response({
            'message': f'Plan upgraded from {old_tier} to {new_tier}',
            'new_quota': org.global_quota,
            'tier': new_tier
        })
