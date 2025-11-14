"""
Django management command to create test data for development.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from core.models import Organization, Subscription, User, Application


class Command(BaseCommand):
    help = 'Create test data for development'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating test data...'))

        # Create Organization
        org, org_created = Organization.objects.get_or_create(
            slug='acme-corp',
            defaults={
                'name': 'Acme Corporation',
                'default_config': {
                    'rate_limit_rpm': 1000,
                    'enable_r1_realtime': True,
                    'redaction_rules': ['$.password', '$.ssn', '$.credit_card'],
                    'alert_email': 'security@acme.com'
                }
            }
        )

        if org_created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created organization: {org.name} ({org.org_id})'))
        else:
            self.stdout.write(f'  Organization already exists: {org.name}')

        # Create Subscription
        subscription, sub_created = Subscription.objects.get_or_create(
            org=org,
            is_active=True,
            defaults={
                'plan_tier': 'pro',
                'quota_max_applications': 5,
                'quota_max_users': 20,
                'quota_requests_per_month': 10_000_000,
                'features': {
                    'r1_realtime': True,
                    'r1_batch': True,
                    'threat_hunting': True,
                    'shift_left': False
                },
                'valid_from': timezone.now(),
            }
        )

        if sub_created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created subscription: {subscription.plan_tier} ({subscription.subscription_id})'))
        else:
            self.stdout.write(f'  Subscription already exists: {subscription.plan_tier}')

        # Create Admin User
        admin_user, admin_created = User.objects.get_or_create(
            email='admin@acme.com',
            defaults={
                'org': org,
                'password_hash': make_password('admin123'),
                'full_name': 'Admin User',
                'role': 'admin',
                'is_active': True
            }
        )

        if admin_created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created admin user: {admin_user.email} (password: admin123)'))
        else:
            self.stdout.write(f'  Admin user already exists: {admin_user.email}')

        # Create Analyst User
        analyst_user, analyst_created = User.objects.get_or_create(
            email='analyst@acme.com',
            defaults={
                'org': org,
                'password_hash': make_password('analyst123'),
                'full_name': 'Analyst User',
                'role': 'analyst',
                'is_active': True
            }
        )

        if analyst_created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created analyst user: {analyst_user.email} (password: analyst123)'))
        else:
            self.stdout.write(f'  Analyst user already exists: {analyst_user.email}')

        # Create Viewer User
        viewer_user, viewer_created = User.objects.get_or_create(
            email='viewer@acme.com',
            defaults={
                'org': org,
                'password_hash': make_password('viewer123'),
                'full_name': 'Viewer User',
                'role': 'viewer',
                'is_active': True
            }
        )

        if viewer_created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created viewer user: {viewer_user.email} (password: viewer123)'))
        else:
            self.stdout.write(f'  Viewer user already exists: {viewer_user.email}')

        # Create Application 1: Payment API
        app1, app1_created = Application.objects.get_or_create(
            org=org,
            slug='payment-api',
            defaults={
                'name': 'Payment API',
                'domain': 'api.acme-payments.com',
                'origin_url': 'https://backend-payments.acme.com',
                'cname_target': 'sentrix-edge-us-east.example.com',
                'custom_config': {
                    'rate_limit_rpm': 5000,  # Override org default
                    'enable_captcha_challenge': True
                },
                'failover_mode': 'fail_open',
                'dns_verified': True,
                'dns_verified_at': timezone.now(),
                'is_active': True
            }
        )

        if app1_created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created application: {app1.name} ({app1.app_id})'))
        else:
            self.stdout.write(f'  Application already exists: {app1.name}')

        # Create Application 2: Logistics API
        app2, app2_created = Application.objects.get_or_create(
            org=org,
            slug='logistics-api',
            defaults={
                'name': 'Logistics API',
                'domain': 'api.acme-logistics.com',
                'origin_url': 'https://backend-logistics.acme.com',
                'cname_target': 'sentrix-edge-us-east.example.com',
                'custom_config': {
                    'rate_limit_rpm': 2000,
                    'blocked_countries': ['CN', 'RU']
                },
                'failover_mode': 'fail_open',
                'dns_verified': True,
                'dns_verified_at': timezone.now(),
                'is_active': True
            }
        )

        if app2_created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created application: {app2.name} ({app2.app_id})'))
        else:
            self.stdout.write(f'  Application already exists: {app2.name}')

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Test data created successfully!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write('Organization:')
        self.stdout.write(f'  Name: {org.name}')
        self.stdout.write(f'  Slug: {org.slug}')
        self.stdout.write(f'  ID: {org.org_id}')
        self.stdout.write('')
        self.stdout.write('Subscription:')
        self.stdout.write(f'  Plan: {subscription.plan_tier}')
        self.stdout.write(f'  Apps quota: {subscription.quota_max_applications}')
        self.stdout.write(f'  Users quota: {subscription.quota_max_users}')
        self.stdout.write('')
        self.stdout.write('Users:')
        self.stdout.write(f'  Admin: admin@acme.com (password: admin123)')
        self.stdout.write(f'  Analyst: analyst@acme.com (password: analyst123)')
        self.stdout.write(f'  Viewer: viewer@acme.com (password: viewer123)')
        self.stdout.write('')
        self.stdout.write('Applications:')
        self.stdout.write(f'  1. {app1.name} ({app1.domain})')
        self.stdout.write(f'  2. {app2.name} ({app2.domain})')
        self.stdout.write('')
        self.stdout.write('Next steps:')
        self.stdout.write('  1. Login: POST /v1/auth/login/ with email & password')
        self.stdout.write('  2. Get token and use: Authorization: Bearer <token>')
        self.stdout.write('  3. Test APIs: /v1/organizations/, /v1/applications/, etc.')
        self.stdout.write('')
