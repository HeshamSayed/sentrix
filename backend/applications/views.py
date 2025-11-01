"""Application views with API key validation for Edge service"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from urllib.parse import urlparse

from applications.models import Application, Environment
from applications.serializers import ApplicationSerializer, EnvironmentSerializer


class ApplicationViewSet(viewsets.ModelViewSet):
    """Application CRUD operations"""
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """
        Allow unauthenticated access to validate_key and resolve_host for Edge service
        """
        # Check both action and path to ensure we catch the request early
        action = getattr(self, 'action', None)
        request_path = getattr(getattr(self, 'request', None), 'path', '')
        
        if action in ['validate_key', 'resolve_host', 'dns_setup', 'dns_verify'] or \
           'validate_key' in request_path or 'resolve_host' in request_path or 'resolve-host' in request_path:
            return [AllowAny()]
        return super().get_permissions()
    
    def get_authenticators(self):
        """
        Skip authentication for public endpoints (service-to-service calls)
        """
        # Check if this is a public endpoint by looking at the request path
        request_path = getattr(self.request, 'path', '')
        if 'validate_key' in request_path or 'resolve_host' in request_path or 'resolve-host' in request_path:
            return []
        return super().get_authenticators()
    
    def get_queryset(self):
        """Filter by user's organizations (skip for public endpoints)"""
        # For public endpoints, return all applications (they have their own auth logic)
        if not self.request.user or not self.request.user.is_authenticated:
            return Application.objects.all()
        
        # For authenticated users, filter by their organizations
        return Application.objects.filter(
            environment__organization__users=self.request.user
        )
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def validate_key(self, request):
        """
        Validate API key and return application configuration
        Used by SENTRIX Edge service to validate requests
        
        GET /api/applications/validate-key/
        Header: X-API-Key: <api_key>
        """
        api_key = request.headers.get('X-API-Key') or request.headers.get('X-SENTRIX-Key')
        
        if not api_key:
            return Response({
                'error': 'missing_api_key',
                'message': 'API key required in X-API-Key or X-SENTRIX-Key header'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            application = Application.objects.select_related('environment__organization').get(
                api_key=api_key
            )
            
            # Check if traffic is enabled
            if not application.is_traffic_enabled:
                return Response({
                    'error': 'traffic_disabled',
                    'message': 'Traffic is disabled for this application'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Return application config for Edge service
            return Response({
                'id': str(application.id),
                'name': application.name,
                'organization_id': str(application.environment.organization.id),
                'target_url': application.target_url,
                'is_traffic_enabled': application.is_traffic_enabled,
                'blocked_countries': application.blocked_countries,
                'allowed_countries': application.allowed_countries,
                'blocked_ips': application.blocked_ips,
                'allowed_ips': application.allowed_ips,
                'rate_limit': 1000,  # requests per minute
                'allocated_quota': application.allocated_quota,
                'used_quota': application.used_quota,
                'origin_signature_key': application.origin_signature_key or 'sentrix-protected',
            })
            
        except Application.DoesNotExist:
            return Response({
                'error': 'invalid_api_key',
                'message': 'Invalid API key'
            }, status=status.HTTP_401_UNAUTHORIZED)


    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def resolve_host(self, request):
        """
        Resolve application configuration by Host header/domain for DNS onboarding.
        GET /api/applications/resolve-host/?host=api.x.com
        Returns same payload as validate_key when traffic_mode='dns' and dns_status='verified'.
        """
        host = request.query_params.get('host') or request.headers.get('host') or ''
        host = host.split(':')[0].strip().lower()
        if not host:
            return Response({
                'error': 'missing_host',
                'message': 'Host is required in query ?host= or Host header'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            application = Application.objects.select_related('environment__organization').get(
                protected_domain__iexact=host,
                traffic_mode='dns',
                dns_status='verified',
                is_active=True,
                is_traffic_enabled=True
            )
        except Application.DoesNotExist:
            return Response({
                'error': 'unrecognized_host',
                'message': 'This hostname is not configured for DNS onboarding or not verified.'
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'id': str(application.id),
            'name': application.name,
            'organization_id': str(application.environment.organization.id),
            'target_url': application.target_url,
            'is_traffic_enabled': application.is_traffic_enabled,
            'blocked_countries': application.blocked_countries,
            'allowed_countries': application.allowed_countries,
            'blocked_ips': application.blocked_ips,
            'allowed_ips': application.allowed_ips,
            'rate_limit': application.rate_limit_per_minute,
            'allocated_quota': application.allocated_quota,
            'used_quota': application.used_quota,
            'origin_signature_key': application.origin_signature_key,
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def dns_setup(self, request):
        """
        Configure DNS onboarding for an application.
        Body: { application_id, protected_domain }
        Generates verification token and returns DNS instructions.
        """
        application_id = request.data.get('application_id')
        protected_domain = (request.data.get('protected_domain') or '').strip().lower()
        if not application_id or not protected_domain:
            return Response({'error': 'invalid_input', 'message': 'application_id and protected_domain are required.'}, status=status.HTTP_400_BAD_REQUEST)

        application = get_object_or_404(
            Application.objects.select_related('environment__organization'),
            id=application_id,
            environment__organization__users=request.user
        )

        token = get_random_string(32)
        edge_hostname = f"c-{str(application.id)[:8]}.edge.sentrix.io"
        bypass_token = get_random_string(48)  # Emergency bypass
        signature_key = get_random_string(64)  # For signing requests

        application.protected_domain = protected_domain
        application.edge_hostname = edge_hostname
        application.dns_verification_token = token
        application.bypass_token = bypass_token
        application.origin_signature_key = signature_key
        application.traffic_mode = 'dns'
        application.dns_status = 'pending'
        application.save()

        return Response({
            'message': 'DNS onboarding initialized',
            'application_id': str(application.id),
            'protected_domain': protected_domain,
            'edge_hostname': edge_hostname,
            'verification': {
                'txt_name': f"_sentrix-verify.{protected_domain}",
                'txt_value': token,
                'cname_name': protected_domain,
                'cname_value': edge_hostname
            },
            'failover': {
                'bypass_token': bypass_token,
                'signature_key': signature_key,
                'instructions': [
                    'Configure origin to validate X-SENTRIX-Signature header',
                    'For emergency bypass (if SENTRIX down), accept X-SENTRIX-Bypass header with bypass_token',
                    'See ZERO_DOWNTIME_FAILOVER.md for nginx configuration examples'
                ]
            },
            'instructions': [
                '1) Create TXT record to verify domain ownership',
                '2) Point your subdomain to SENTRIX via CNAME',
                '3) (Optional) Configure origin failover protection',
                '4) Click verify to activate'
            ]
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def dns_verify(self, request):
        """
        Verify DNS for an application by checking TXT and CNAME records.
        Body: { application_id }
        """
        try:
            import dns.resolver  # dnspython
        except Exception:
            return Response({'error': 'server_missing_dependency', 'message': 'dnspython is not installed on the server.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        application_id = request.data.get('application_id')
        application = get_object_or_404(
            Application.objects.select_related('environment__organization'),
            id=application_id,
            environment__organization__users=request.user
        )

        domain = (application.protected_domain or '').strip().lower()
        if not domain or not application.dns_verification_token:
            return Response({'error': 'not_configured', 'message': 'DNS onboarding not configured for this application.'}, status=status.HTTP_400_BAD_REQUEST)

        txt_name = f"_sentrix-verify.{domain}"
        token_ok = False
        cname_ok = False

        try:
            answers = dns.resolver.resolve(txt_name, 'TXT')
            for rdata in answers:
                vals = [s.decode('utf-8') if isinstance(s, bytes) else str(s) for s in rdata.strings]
                if application.dns_verification_token in vals:
                    token_ok = True
                    break
        except Exception:
            token_ok = False

        try:
            answers = dns.resolver.resolve(domain, 'CNAME')
            for rdata in answers:
                target = str(rdata.target).rstrip('.')
                if target.lower() == (application.edge_hostname or '').lower():
                    cname_ok = True
                    break
        except Exception:
            cname_ok = False

        if token_ok and cname_ok:
            application.dns_status = 'verified'
            application.save(update_fields=['dns_status'])
            return Response({'message': 'DNS verified successfully', 'status': 'verified'})
        else:
            application.dns_status = 'failed'
            application.save(update_fields=['dns_status'])
            return Response({
                'message': 'DNS verification failed',
                'status': 'failed',
                'token_ok': token_ok,
                'cname_ok': cname_ok,
                'expected_cname': application.edge_hostname,
                'txt_name': txt_name,
                'expected_token': application.dns_verification_token
            }, status=status.HTTP_400_BAD_REQUEST)
class EnvironmentViewSet(viewsets.ModelViewSet):
    """Environment CRUD operations"""
    serializer_class = EnvironmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter by application"""
        application_id = self.request.query_params.get('application_id')
        queryset = Environment.objects.filter(
            application__organization__users=self.request.user
        )
        
        if application_id:
            queryset = queryset.filter(application_id=application_id)
        
        return queryset
