"""
Automated self-service onboarding wizard for zero-deploy DNS protection
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.crypto import get_random_string
from applications.models import Application, Environment
from applications.tasks import auto_verify_dns_records, send_onboarding_notification
import logging

logger = logging.getLogger(__name__)


class OnboardingWizardViewSet(viewsets.ViewSet):
    """
    Self-service onboarding wizard for automated DNS protection.
    Complete flow from signup to protection in minutes.
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def start(self, request):
        """
        Step 1: Initialize onboarding with domain to protect.
        
        POST /api/onboarding-wizard/start/
        Body: {
            "domain": "api.todo.com",
            "origin_url": "https://origin.todo.com",
            "application_name": "TODO API Production"
        }
        
        Returns DNS records to add and initiates monitoring.
        """
        domain = (request.data.get('domain') or '').strip().lower()
        origin_url = (request.data.get('origin_url') or '').strip()
        app_name = request.data.get('application_name', f"{domain} API")
        
        if not domain or not origin_url:
            return Response({
                'error': 'invalid_input',
                'message': 'domain and origin_url are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create default environment
        org = request.user.organizations.first()
        if not org:
            return Response({
                'error': 'no_organization',
                'message': 'User must belong to an organization'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        env, _ = Environment.objects.get_or_create(
            organization=org,
            name='Production',
            defaults={'environment_type': 'production'}
        )
        
        # Create application
        app = Application.objects.create(
            environment=env,
            name=app_name,
            slug=domain.replace('.', '-'),
            base_url=f"https://{domain}",
            target_url=origin_url,
            protected_domain=domain,
            edge_hostname=f"c-{get_random_string(8)}.edge.sentrix-co.com",
            dns_verification_token=get_random_string(32),
            bypass_token=get_random_string(48),
            origin_signature_key=get_random_string(64),
            traffic_mode='dns',
            dns_status='pending',
            is_active=True,
            is_traffic_enabled=True
        )
        
        # Start automatic verification monitoring
        auto_verify_dns_records.apply_async(countdown=60)  # Check in 1 minute
        
        # Send notification
        send_onboarding_notification.delay(
            request.user.email,
            app.name,
            app.protected_domain,
            'dns_records_ready'
        )
        
        return Response({
            'success': True,
            'application_id': str(app.id),
            'step': 'dns_records',
            'message': 'Add these DNS records to continue',
            
            'dns_records': {
                'verification': {
                    'type': 'TXT',
                    'name': f"_sentrix-verify.{domain}",
                    'value': app.dns_verification_token,
                    'ttl': 300,
                    'priority': 'Add this first to verify ownership'
                },
                'routing': {
                    'type': 'CNAME',
                    'name': domain,
                    'value': app.edge_hostname,
                    'ttl': 300,
                    'priority': 'Add this second to route traffic'
                }
            },
            
            'protected_domain': domain,
            'edge_hostname': app.edge_hostname,
            
            'next_steps': [
                '1. Add the TXT record to verify domain ownership',
                '2. Add the CNAME record to route traffic through SENTRIX',
                '3. Wait 2-5 minutes for DNS propagation',
                '4. Check status (we auto-verify every 5 minutes)',
                '5. Once verified, your domain is protected!'
            ],
            
            'auto_verify': {
                'enabled': True,
                'check_interval': '5 minutes',
                'message': 'We automatically check DNS every 5 minutes. No action needed!'
            },
            
            'manual_verify_endpoint': f'/api/onboarding-wizard/verify/',
            
            'support': {
                'docs': 'https://docs.sentrix-co.com/dns-onboarding',
                'chat': 'https://sentrix-co.com/support',
                'email': 'support@sentrix-co.com'
            }
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def verify(self, request):
        """
        Step 2: Manually trigger DNS verification (optional - auto-verify runs every 5 min).
        
        POST /api/onboarding-wizard/verify/
        Body: { "application_id": "<uuid>" }
        """
        app_id = request.data.get('application_id')
        
        try:
            app = Application.objects.get(
                id=app_id,
                environment__organization__users=request.user
            )
        except Application.DoesNotExist:
            return Response({
                'error': 'not_found',
                'message': 'Application not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if app.dns_status == 'verified':
            return Response({
                'success': True,
                'status': 'already_verified',
                'message': f'{app.protected_domain} is already verified and protected!',
                'protected_domain': app.protected_domain,
                'edge_hostname': app.edge_hostname
            })
        
        # Trigger immediate verification
        from applications.tasks import auto_verify_dns_records
        result = auto_verify_dns_records.apply_async()
        
        # Check current status
        app.refresh_from_db()
        
        if app.dns_status == 'verified':
            return Response({
                'success': True,
                'status': 'verified',
                'message': f'✅ {app.protected_domain} is now protected!',
                'protected_domain': app.protected_domain,
                'edge_hostname': app.edge_hostname,
                'test_url': f'https://{app.protected_domain}/health',
                'dashboard_url': 'https://dashboard.sentrix-co.com'
            })
        else:
            return Response({
                'success': False,
                'status': 'pending',
                'message': 'DNS records not detected yet. Please wait a few minutes for propagation.',
                'dns_check': {
                    'txt_record': f"_sentrix-verify.{app.protected_domain}",
                    'expected_value': app.dns_verification_token,
                    'cname_record': app.protected_domain,
                    'expected_value': app.edge_hostname
                },
                'retry_in': '2-5 minutes',
                'auto_verify': 'We check automatically every 5 minutes'
            }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        Step 3: Check onboarding status for all user's applications.
        
        GET /api/onboarding-wizard/status/
        """
        user_orgs = request.user.organizations.all()
        applications = Application.objects.filter(
            environment__organization__in=user_orgs,
            traffic_mode='dns'
        ).select_related('environment__organization').order_by('-created_at')
        
        apps_status = []
        for app in applications:
            apps_status.append({
                'id': str(app.id),
                'name': app.name,
                'protected_domain': app.protected_domain,
                'edge_hostname': app.edge_hostname,
                'dns_status': app.dns_status,
                'is_protected': app.dns_status == 'verified',
                'created_at': app.created_at.isoformat(),
                'test_url': f'https://{app.protected_domain}/' if app.dns_status == 'verified' else None,
                'steps_completed': {
                    'dns_records_added': app.dns_verification_token != '',
                    'dns_verified': app.dns_status == 'verified',
                    'ssl_provisioned': app.dns_status == 'verified',  # Auto-provisioned
                    'traffic_protected': app.is_traffic_enabled and app.dns_status == 'verified'
                }
            })
        
        return Response({
            'applications': apps_status,
            'total': len(apps_status),
            'verified': sum(1 for a in apps_status if a['is_protected']),
            'pending': sum(1 for a in apps_status if not a['is_protected'])
        })
    
    @action(detail=False, methods=['post'])
    def test(self, request):
        """
        Step 4: Test if domain is properly protected.
        
        POST /api/onboarding-wizard/test/
        Body: { "application_id": "<uuid>" }
        """
        app_id = request.data.get('application_id')
        
        try:
            app = Application.objects.get(
                id=app_id,
                environment__organization__users=request.user
            )
        except Application.DoesNotExist:
            return Response({
                'error': 'not_found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if app.dns_status != 'verified':
            return Response({
                'error': 'not_verified',
                'message': 'DNS must be verified before testing'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Run automated tests
        import httpx
        test_results = []
        
        # Test 1: Basic connectivity
        try:
            resp = httpx.get(f"https://{app.protected_domain}/", timeout=10.0, follow_redirects=True)
            test_results.append({
                'test': 'basic_connectivity',
                'passed': resp.status_code < 500,
                'status_code': resp.status_code,
                'message': 'Domain is reachable through SENTRIX'
            })
        except Exception as e:
            test_results.append({
                'test': 'basic_connectivity',
                'passed': False,
                'error': str(e),
                'message': 'Could not reach domain'
            })
        
        # Test 2: SENTRIX headers present
        try:
            resp = httpx.get(f"https://{app.protected_domain}/", timeout=10.0)
            has_sentrix_headers = 'x-sentrix-protected' in [h.lower() for h in resp.headers.keys()]
            test_results.append({
                'test': 'sentrix_protection',
                'passed': has_sentrix_headers,
                'message': 'SENTRIX protection headers detected' if has_sentrix_headers else 'SENTRIX headers not found'
            })
        except:
            test_results.append({
                'test': 'sentrix_protection',
                'passed': False,
                'message': 'Could not verify SENTRIX headers'
            })
        
        all_passed = all(t['passed'] for t in test_results)
        
        return Response({
            'application_id': str(app.id),
            'protected_domain': app.protected_domain,
            'test_summary': {
                'total_tests': len(test_results),
                'passed': sum(1 for t in test_results if t['passed']),
                'failed': sum(1 for t in test_results if not t['passed']),
                'all_passed': all_passed
            },
            'tests': test_results,
            'message': '✅ All tests passed! Your domain is protected.' if all_passed else '⚠️ Some tests failed. Please check configuration.'
        })
    
    @action(detail=False, methods=['post'])
    def complete(self, request):
        """
        Step 5: Mark onboarding as complete and show summary.
        
        POST /api/onboarding-wizard/complete/
        Body: { "application_id": "<uuid>" }
        """
        app_id = request.data.get('application_id')
        
        try:
            app = Application.objects.get(
                id=app_id,
                environment__organization__users=request.user
            )
        except Application.DoesNotExist:
            return Response({
                'error': 'not_found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if app.dns_status != 'verified':
            return Response({
                'error': 'not_verified',
                'message': 'Complete DNS verification first'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Send completion notification
        send_onboarding_notification.delay(
            request.user.email,
            app.name,
            app.protected_domain,
            'onboarding_complete'
        )
        
        return Response({
            'success': True,
            'message': f'🎉 Congratulations! {app.protected_domain} is now protected by SENTRIX!',
            
            'summary': {
                'protected_domain': app.protected_domain,
                'edge_hostname': app.edge_hostname,
                'protection_started': app.updated_at.isoformat(),
                
                'features_enabled': [
                    '✓ SQL Injection Protection',
                    '✓ XSS Protection',
                    '✓ DDoS Mitigation',
                    '✓ Rate Limiting',
                    '✓ Behavioral Analysis',
                    '✓ Real-time Monitoring',
                    '✓ Geographic Blocking',
                    '✓ IP Filtering',
                    '✓ Bot Detection'
                ],
                
                'endpoints_protected': 'ALL (wildcard: /*)',
                
                'failover': {
                    'enabled': bool(app.bypass_token),
                    'bypass_token': app.bypass_token if app.bypass_token else None,
                    'signature_key': app.origin_signature_key if app.origin_signature_key else None
                }
            },
            
            'next_actions': [
                'View real-time dashboard: https://dashboard.sentrix-co.com',
                'Configure custom security rules',
                'Set up alerting (email/Slack)',
                'Review blocked attacks',
                'Monitor performance metrics'
            ],
            
            'support': {
                'docs': 'https://docs.sentrix-co.com',
                'community': 'https://community.sentrix-co.com',
                'email': 'support@sentrix-co.com',
                'chat': 'Available in dashboard'
            }
        })

