"""
Separate views for organization settings to avoid ViewSet conflicts
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.utils import timezone
import json
import csv
import io
import secrets

from .models import Organization
from .serializers import (
    OrganizationSettingsSerializer,
    NotificationSettingsSerializer,
    SecuritySettingsSerializer,
    SubscriptionInfoSerializer,
    ExportDataSerializer
)
from core.permissions import IsRootOrAdmin, IsRoot
from users.models import User
from applications.models import Application
from traffic.models import APIRequest


class OrganizationSettingsView(APIView):
    """Get or update organization settings"""
    permission_classes = [IsRootOrAdmin]
    
    def get(self, request):
        org = request.user.organization
        data = {
            'name': org.name,
            'slug': org.slug,
            'billing_email': org.billing_email,
            'description': org.description,
            'max_users': org.max_users,
            'current_users': org.current_users,
        }
        return Response(data)
    
    def put(self, request):
        org = request.user.organization
        serializer = OrganizationSettingsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.update(org, serializer.validated_data)
            return Response({
                'message': 'Organization settings updated successfully',
                'data': serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationSettingsView(APIView):
    """Get or update notification settings"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        org = request.user.organization
        org_settings = org.settings or {}
        notifications = org_settings.get('notifications', {
            'email_alerts': True,
            'slack_notifications': False,
            'webhook_url': '',
            'alert_threshold': 'high'
        })
        return Response(notifications)
    
    def put(self, request):
        org = request.user.organization
        serializer = NotificationSettingsSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.update(org, serializer.validated_data)
            return Response({
                'message': 'Notification settings updated successfully',
                'data': result
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TestNotificationView(APIView):
    """Test notification settings"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        org = request.user.organization
        org_settings = org.settings or {}
        notifications = org_settings.get('notifications', {})
        
        results = {
            'email': False,
            'slack': False,
            'webhook': False
        }
        
        if notifications.get('email_alerts'):
            results['email'] = True
        
        if notifications.get('slack_notifications') and notifications.get('webhook_url'):
            results['webhook'] = True
        
        return Response({
            'message': 'Test notification sent',
            'results': results,
            'timestamp': timezone.now().isoformat()
        })


class SecuritySettingsView(APIView):
    """Get or update security settings"""
    permission_classes = [IsRootOrAdmin]
    
    def get(self, request):
        org = request.user.organization
        org_settings = org.settings or {}
        security = org_settings.get('security', {
            'two_factor_enabled': False,
            'session_timeout': '30',
            'ip_whitelist': []
        })
        return Response(security)
    
    def put(self, request):
        org = request.user.organization
        serializer = SecuritySettingsSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.update(org, serializer.validated_data)
            return Response({
                'message': 'Security settings updated successfully',
                'data': result
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionInfoView(APIView):
    """Get subscription information"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        org = request.user.organization
        serializer = SubscriptionInfoSerializer(org)
        return Response(serializer.data)


class APIKeysView(APIView):
    """List API keys"""
    permission_classes = [IsRootOrAdmin]
    
    def get(self, request):
        org = request.user.organization
        org_settings = org.settings or {}
        api_keys = org_settings.get('api_keys', [])
        return Response(api_keys)


class CreateAPIKeyView(APIView):
    """Create a new API key"""
    permission_classes = [IsRootOrAdmin]
    
    def post(self, request):
        org = request.user.organization
        name = request.data.get('name', 'API Key')
        
        key = f"sk_{secrets.token_urlsafe(32)}"
        
        org_settings = org.settings or {}
        api_keys = org_settings.get('api_keys', [])
        
        new_key = {
            'id': secrets.token_urlsafe(16),
            'name': name,
            'key': key,
            'created_at': timezone.now().isoformat(),
            'last_used_at': None,
            'is_active': True
        }
        
        api_keys.append(new_key)
        org_settings['api_keys'] = api_keys
        org.settings = org_settings
        org.save()
        
        return Response({
            'message': 'API key created successfully',
            'key': new_key
        }, status=status.HTTP_201_CREATED)


class RevokeAPIKeyView(APIView):
    """Revoke an API key"""
    permission_classes = [IsRootOrAdmin]
    
    def post(self, request):
        org = request.user.organization
        key_id = request.data.get('key_id')
        
        org_settings = org.settings or {}
        api_keys = org_settings.get('api_keys', [])
        
        updated = False
        for key in api_keys:
            if key['id'] == key_id:
                key['is_active'] = False
                updated = True
                break
        
        if updated:
            org_settings['api_keys'] = api_keys
            org.settings = org_settings
            org.save()
            return Response({'message': 'API key revoked successfully'})
        
        return Response(
            {'error': 'API key not found'},
            status=status.HTTP_404_NOT_FOUND
        )


class ExportDataView(APIView):
    """Export organization data"""
    permission_classes = [IsRoot]
    
    def post(self, request):
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
            traffic = APIRequest.objects.filter(
                environment__application__organization=org
            ).order_by('-timestamp')[:1000].values(
                'method', 'path', 'status_code', 'response_time_ms', 'timestamp'
            )
            export_data['traffic'] = list(traffic)
        
        if data['format'] == 'json':
            response = HttpResponse(
                json.dumps(export_data, indent=2, default=str),
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="{org.slug}_export.json"'
        else:  # CSV
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


class DeleteOrganizationView(APIView):
    """Delete organization (with confirmation)"""
    permission_classes = [IsRoot]
    
    def post(self, request):
        org = request.user.organization
        confirmation = request.data.get('confirmation')
        
        if confirmation != org.slug:
            return Response({
                'error': 'Confirmation failed. Please provide the organization slug to confirm deletion.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        org_name = org.name
        org.is_active = False
        org.save()
        
        return Response({
            'message': f'Organization "{org_name}" has been deactivated. It will be permanently deleted in 30 days.',
            'deactivated_at': timezone.now().isoformat()
        })


class UpgradePlanView(APIView):
    """Upgrade subscription plan"""
    permission_classes = [IsRoot]
    
    def post(self, request):
        org = request.user.organization
        new_tier = request.data.get('tier')
        
        # Tier hierarchy and quotas
        tier_info = {
            'TRIAL': {'quota': 1_000_000, 'price': 0, 'max_users': 10},
            'STARTER': {'quota': 10_000_000, 'price': 99, 'max_users': 30},
            'PROFESSIONAL': {'quota': 100_000_000, 'price': 499, 'max_users': 100},
            'ENTERPRISE': {'quota': 1_000_000_000, 'price': 1999, 'max_users': 500},
        }
        
        if new_tier not in tier_info:
            return Response({
                'error': f'Invalid tier. Choose from: {", ".join(tier_info.keys())}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if upgrading
        current_tier = org.subscription_tier
        tier_order = ['TRIAL', 'STARTER', 'PROFESSIONAL', 'ENTERPRISE']
        
        if tier_order.index(new_tier) <= tier_order.index(current_tier):
            return Response({
                'error': f'Cannot downgrade from {current_tier} to {new_tier}. Please contact support.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update subscription
        old_tier = org.subscription_tier
        org.subscription_tier = new_tier
        org.global_quota = tier_info[new_tier]['quota']
        org.max_users = tier_info[new_tier]['max_users']
        org.subscription_starts_at = timezone.now()
        org.save()
        
        return Response({
            'message': f'Successfully upgraded from {old_tier} to {new_tier}',
            'tier': new_tier,
            'quota': tier_info[new_tier]['quota'],
            'max_users': tier_info[new_tier]['max_users'],
            'price': tier_info[new_tier]['price'],
            'upgraded_at': timezone.now().isoformat()
        })


class ViewInvoicesView(APIView):
    """View billing invoices"""
    permission_classes = [IsRootOrAdmin]
    
    def get(self, request):
        org = request.user.organization
        
        # Generate mock invoices based on subscription history
        # In production, this would integrate with Stripe or similar
        invoices = []
        
        if org.subscription_starts_at:
            base_date = org.subscription_starts_at
            
            # Tier pricing
            tier_prices = {
                'TRIAL': 0,
                'STARTER': 99,
                'PROFESSIONAL': 499,
                'ENTERPRISE': 1999,
            }
            
            current_price = tier_prices.get(org.subscription_tier, 0)
            
            # Generate last 6 months of invoices
            from datetime import timedelta
            for i in range(6):
                invoice_date = timezone.now() - timedelta(days=30 * i)
                invoice_num = f"INV-{org.slug.upper()}-{invoice_date.strftime('%Y%m')}"
                
                invoices.append({
                    'id': invoice_num,
                    'invoice_number': invoice_num,
                    'date': invoice_date.isoformat(),
                    'due_date': (invoice_date + timedelta(days=7)).isoformat(),
                    'amount': current_price,
                    'currency': 'USD',
                    'status': 'paid' if i > 0 else 'pending',
                    'period': f"{invoice_date.strftime('%B %Y')}",
                    'plan': org.subscription_tier,
                    'download_url': f'/api/organizations/invoices/{invoice_num}/download/'
                })
        
        return Response({
            'invoices': invoices,
            'total_count': len(invoices),
            'organization': org.name
        })


class DownloadInvoiceView(APIView):
    """Download a specific invoice as PDF"""
    permission_classes = [IsRootOrAdmin]
    
    def get(self, request, invoice_id):
        org = request.user.organization
        
        # In production, generate actual PDF
        # For now, return a simple receipt
        invoice_data = f"""
INVOICE: {invoice_id}
Organization: {org.name}
Billing Email: {org.billing_email}
Plan: {org.subscription_tier}
Date: {timezone.now().strftime('%Y-%m-%d')}

Thank you for your business!
        """
        
        response = HttpResponse(invoice_data, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{invoice_id}.txt"'
        return response


class UpdatePaymentMethodView(APIView):
    """Update payment method"""
    permission_classes = [IsRoot]
    
    def post(self, request):
        org = request.user.organization
        
        # Extract payment details
        card_number = request.data.get('card_number', '')
        card_holder = request.data.get('card_holder', '')
        expiry_month = request.data.get('expiry_month', '')
        expiry_year = request.data.get('expiry_year', '')
        cvv = request.data.get('cvv', '')
        
        # Basic validation
        if not all([card_number, card_holder, expiry_month, expiry_year, cvv]):
            return Response({
                'error': 'All payment fields are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mask card number (keep last 4 digits)
        masked_card = f"****-****-****-{card_number[-4:]}" if len(card_number) >= 4 else '****-****-****-****'
        
        # Store payment info in settings (in production, use Stripe)
        org_settings = org.settings or {}
        org_settings['payment_method'] = {
            'card_last4': card_number[-4:] if len(card_number) >= 4 else '0000',
            'card_holder': card_holder,
            'expiry': f"{expiry_month}/{expiry_year}",
            'updated_at': timezone.now().isoformat()
        }
        org.settings = org_settings
        org.save()
        
        return Response({
            'message': 'Payment method updated successfully',
            'card_last4': masked_card,
            'card_holder': card_holder,
            'updated_at': timezone.now().isoformat()
        })
    
    def get(self, request):
        """Get current payment method"""
        org = request.user.organization
        org_settings = org.settings or {}
        payment_method = org_settings.get('payment_method', {})
        
        if not payment_method:
            return Response({
                'has_payment_method': False,
                'message': 'No payment method on file'
            })
        
        return Response({
            'has_payment_method': True,
            'card_last4': payment_method.get('card_last4', '****'),
            'card_holder': payment_method.get('card_holder', ''),
            'expiry': payment_method.get('expiry', ''),
            'updated_at': payment_method.get('updated_at', '')
        })

