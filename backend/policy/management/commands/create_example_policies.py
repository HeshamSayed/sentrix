"""
Django management command to create example policies.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Organization, Application, User
from policy.models import Policy


class Command(BaseCommand):
    help = 'Create example security policies for testing and demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--org-slug',
            type=str,
            help='Organization slug (default: first org)',
        )
        parser.add_argument(
            '--app-slug',
            type=str,
            help='Application slug (default: first app)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing example policies first',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # Get organization
        org_slug = options.get('org_slug')
        if org_slug:
            try:
                org = Organization.objects.get(slug=org_slug)
            except Organization.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Organization "{org_slug}" not found'))
                return
        else:
            org = Organization.objects.first()
            if not org:
                self.stdout.write(self.style.ERROR('No organizations found. Run create_test_data first.'))
                return

        # Get application
        app_slug = options.get('app_slug')
        if app_slug:
            try:
                app = Application.objects.get(org=org, slug=app_slug)
            except Application.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Application "{app_slug}" not found'))
                return
        else:
            app = Application.objects.filter(org=org).first()
            if not app:
                self.stdout.write(self.style.WARNING('No applications found. Creating org-level policies only.'))

        # Get first admin user for created_by
        admin_user = User.objects.filter(org=org, role='admin').first()

        # Clear existing example policies if requested
        if options['clear']:
            count = Policy.objects.filter(org=org, description__contains='[Example]').delete()[0]
            self.stdout.write(self.style.WARNING(f'Deleted {count} existing example policies'))

        self.stdout.write(self.style.SUCCESS(f'Creating example policies for org: {org.name}'))
        if app:
            self.stdout.write(self.style.SUCCESS(f'Application: {app.name}'))

        # Example policies
        examples = [
            # 1. Block admin access from external IPs
            {
                'name': 'Block External Admin Access',
                'description': '[Example] Restrict admin panel to internal network',
                'app': app,
                'is_org_level': False,
                'condition': {
                    'and': [
                        {'field': 'path', 'op': 'startswith', 'value': '/admin'},
                        {
                            'not': {
                                'field': 'client_ip',
                                'op': 'in_cidr',
                                'value': '10.0.0.0/8'
                            }
                        }
                    ]
                },
                'action': {
                    'type': 'block',
                    'response_code': 403,
                    'message': 'Admin access restricted to internal network'
                },
                'mode': 'observe',
                'priority': 10,
                'is_enabled': False
            },

            # 2. Rate limit payment endpoints
            {
                'name': 'Throttle Payment Endpoints',
                'description': '[Example] Rate limit high-value payment endpoints',
                'app': app,
                'is_org_level': False,
                'condition': {
                    'field': 'path_pattern',
                    'op': 'in',
                    'value': ['/payments/charge', '/payments/refund', '/payments/transfer']
                },
                'action': {
                    'type': 'throttle',
                    'response_code': 429,
                    'message': 'Too many payment requests. Please try again later.'
                },
                'mode': 'observe',
                'priority': 50,
                'is_enabled': False
            },

            # 3. Block SQL injection patterns
            {
                'name': 'Block SQL Injection Attempts',
                'description': '[Example] Block requests with SQL injection patterns',
                'app': app,
                'is_org_level': False,
                'condition': {
                    'field': 'path',
                    'op': 'regex',
                    'value': '.*(union|select|drop|insert|update|delete|from|where|table|exec|execute).*'
                },
                'action': {
                    'type': 'block',
                    'response_code': 403,
                    'message': 'Malicious request pattern detected'
                },
                'mode': 'observe',
                'priority': 1,
                'is_enabled': False
            },

            # 4. Challenge suspicious user agents
            {
                'name': 'Challenge Bot Traffic',
                'description': '[Example] Require CAPTCHA for bot-like user agents',
                'app': app,
                'is_org_level': False,
                'condition': {
                    'field': 'request_meta.headers.user_agent',
                    'op': 'regex',
                    'value': '.*(bot|crawler|scraper|spider|curl|wget).*'
                },
                'action': {
                    'type': 'challenge',
                    'challenge_type': 'captcha',
                    'message': 'Please complete CAPTCHA verification'
                },
                'mode': 'observe',
                'priority': 100,
                'is_enabled': False
            },

            # 5. Block access to sensitive paths
            {
                'name': 'Block Sensitive Path Access',
                'description': '[Example] Block access to config files and backups',
                'app': app,
                'is_org_level': False,
                'condition': {
                    'or': [
                        {'field': 'path', 'op': 'contains', 'value': '.env'},
                        {'field': 'path', 'op': 'contains', 'value': '.git'},
                        {'field': 'path', 'op': 'contains', 'value': 'backup'},
                        {'field': 'path', 'op': 'contains', 'value': 'config'},
                        {'field': 'path', 'op': 'contains', 'value': '.sql'},
                    ]
                },
                'action': {
                    'type': 'block',
                    'response_code': 404,
                    'message': 'Not found'
                },
                'mode': 'observe',
                'priority': 5,
                'is_enabled': False
            },

            # 6. Org-level: Block known bad countries (example - disabled by default)
            {
                'name': 'Country-Based Blocking',
                'description': '[Example] Organization-wide country blocking (org-level)',
                'app': None,
                'is_org_level': True,
                'condition': {
                    'field': 'geo_country',
                    'op': 'in',
                    'value': ['XX', 'YY']  # Placeholder codes
                },
                'action': {
                    'type': 'block',
                    'response_code': 451,
                    'message': 'Access not available in your region'
                },
                'mode': 'observe',
                'priority': 5,
                'is_enabled': False
            },

            # 7. Block POST requests without Content-Type
            {
                'name': 'Require Content-Type for POST',
                'description': '[Example] Block POST/PUT requests without Content-Type header',
                'app': app,
                'is_org_level': False,
                'condition': {
                    'and': [
                        {
                            'field': 'method',
                            'op': 'in',
                            'value': ['POST', 'PUT', 'PATCH']
                        },
                        {
                            'or': [
                                {'field': 'request_meta.headers.content_type', 'op': 'eq', 'value': None},
                                {'field': 'request_meta.headers.content_type', 'op': 'eq', 'value': ''}
                            ]
                        }
                    ]
                },
                'action': {
                    'type': 'block',
                    'response_code': 400,
                    'message': 'Content-Type header required for POST/PUT requests'
                },
                'mode': 'observe',
                'priority': 20,
                'is_enabled': False
            },

            # 8. Allow only specific HTTP methods
            {
                'name': 'Enforce Allowed HTTP Methods',
                'description': '[Example] Block requests with uncommon HTTP methods',
                'app': app,
                'is_org_level': False,
                'condition': {
                    'field': 'method',
                    'op': 'not_in',
                    'value': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
                },
                'action': {
                    'type': 'block',
                    'response_code': 405,
                    'message': 'Method not allowed'
                },
                'mode': 'observe',
                'priority': 15,
                'is_enabled': False
            },
        ]

        # Create policies
        created_count = 0
        for example in examples:
            try:
                policy = Policy.objects.create(
                    org=org,
                    app=example['app'],
                    name=example['name'],
                    description=example['description'],
                    is_org_level=example['is_org_level'],
                    condition=example['condition'],
                    action=example['action'],
                    mode=example['mode'],
                    priority=example['priority'],
                    is_enabled=example['is_enabled'],
                    created_by=admin_user
                )
                created_count += 1

                scope = 'org-level' if policy.is_org_level else f'app: {app.name if app else "N/A"}'
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Created: {policy.name} ({scope}) - '
                        f'mode={policy.mode}, enabled={policy.is_enabled}, priority={policy.priority}'
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Failed to create: {example["name"]} - {str(e)}')
                )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Created {created_count} example policies'))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Note: All policies are created in OBSERVE mode and DISABLED'))
        self.stdout.write(self.style.WARNING('To enable a policy:'))
        self.stdout.write(self.style.WARNING('  1. Review the policy in Django admin or via API'))
        self.stdout.write(self.style.WARNING('  2. Test with /v1/policy/test/ endpoint'))
        self.stdout.write(self.style.WARNING('  3. Run simulation: POST /v1/policy/policies/{id}/simulate/'))
        self.stdout.write(self.style.WARNING('  4. Enable: POST /v1/policy/policies/{id}/enable/'))
        self.stdout.write(self.style.WARNING('  5. Switch to enforce mode: PATCH /v1/policy/policies/{id}/ {"mode": "enforce"}'))
