from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from organizations.models import Organization
from users.models import User
from applications.models import Application, Environment
from analytics.models import MetricSnapshot, Alert
from traffic.models import APIRequest, ThreatDetection
import random
import uuid

class Command(BaseCommand):
    help = 'Initialize demo data for the platform'

    def handle(self, *args, **options):
        self.stdout.write('Initializing demo data...')
        
        # Create demo organization
        org, created = Organization.objects.get_or_create(
            slug='demo-org',
            defaults={
                'name': 'Demo Organization',
                'description': 'Demo organization for testing',
                'subscription_tier': 'PROFESSIONAL',
                'is_active': True,
                'subscription_starts_at': timezone.now(),
                'subscription_ends_at': timezone.now() + timedelta(days=365),
                'max_users': 30,
                'current_users': 0,
                'global_quota': 10000000,  # 10M API calls
                'used_quota': 2500000,  # 25% used
                'billing_email': 'billing@demo.com',
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created organization: {org.name}'))
        else:
            self.stdout.write(f'Organization already exists: {org.name}')
        
        # Create root user
        root_user, created = User.objects.get_or_create(
            email='admin@demo.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'organization': org,
                'role': 'ROOT',
                'is_active': True,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            root_user.set_password('admin123')
            root_user.save()
            org.current_users += 1
            org.save()
            self.stdout.write(self.style.SUCCESS(f'Created root user: {root_user.email} (password: admin123)'))
        else:
            self.stdout.write(f'Root user already exists: {root_user.email}')
        
        # Create admin user
        admin_user, created = User.objects.get_or_create(
            email='manager@demo.com',
            defaults={
                'first_name': 'Manager',
                'last_name': 'Admin',
                'organization': org,
                'role': 'ADMIN',
                'is_active': True,
            }
        )
        if created:
            admin_user.set_password('manager123')
            admin_user.save()
            org.current_users += 1
            org.save()
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {admin_user.email} (password: manager123)'))
        
        # Create security user
        security_user, created = User.objects.get_or_create(
            email='security@demo.com',
            defaults={
                'first_name': 'Security',
                'last_name': 'Analyst',
                'organization': org,
                'role': 'SECURITY',
                'is_active': True,
            }
        )
        if created:
            security_user.set_password('security123')
            security_user.save()
            org.current_users += 1
            org.save()
            self.stdout.write(self.style.SUCCESS(f'Created security user: {security_user.email} (password: security123)'))
        
        # Create demo applications
        app1, created = Application.objects.get_or_create(
            organization=org,
            slug='api-gateway',
            defaults={
                'name': 'API Gateway',
                'description': 'Main API gateway service',
                'allocated_quota': 5000000,
                'used_quota': 1200000,
                'is_traffic_enabled': True,
                'maintenance_mode': False,
                'blocked_countries': ['CN', 'KP'],
                'blocked_ips': ['192.0.2.1'],
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created application: {app1.name}'))
        
        app2, created = Application.objects.get_or_create(
            organization=org,
            slug='mobile-api',
            defaults={
                'name': 'Mobile API',
                'description': 'API for mobile applications',
                'allocated_quota': 3000000,
                'used_quota': 800000,
                'is_traffic_enabled': True,
                'maintenance_mode': False,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created application: {app2.name}'))
        
        # Create environments
        for app in [app1, app2]:
            for env_name in ['PRODUCTION', 'STAGING', 'DEVELOPMENT']:
                env, created = Environment.objects.get_or_create(
                    application=app,
                    name=env_name,
                    defaults={
                        'base_domain': f'{env_name.lower()}.{app.slug}.demo.com',
                        'is_active': True,
                        'resources': {
                            'cpu': '2 cores',
                            'memory': '4GB',
                            'instances': 3 if env_name == 'PRODUCTION' else 1
                        }
                    }
                )
                if created:
                    self.stdout.write(f'  Created environment: {app.name} - {env_name}')
        
        # Create sample metrics for the last 24 hours
        self.stdout.write('Creating sample metrics...')
        now = timezone.now()
        for hour in range(24):
            timestamp = now - timedelta(hours=hour)
            for app in [app1, app2]:
                MetricSnapshot.objects.get_or_create(
                    application=app,
                    timestamp=timestamp,
                    granularity='HOUR',
                    defaults={
                        'total_requests': random.randint(10000, 50000),
                        'successful_requests': random.randint(9000, 48000),
                        'failed_requests': random.randint(100, 2000),
                        'blocked_requests': random.randint(10, 500),
                        'avg_response_time_ms': random.uniform(50, 200),
                        'p95_response_time_ms': random.uniform(150, 400),
                        'p99_response_time_ms': random.uniform(300, 600),
                        'threat_count': random.randint(0, 10),
                        'high_risk_requests': random.randint(0, 50),
                        'unique_ips': random.randint(500, 2000),
                        'unique_endpoints': random.randint(20, 100),
                        'bytes_sent': random.randint(1000000, 10000000),
                        'bytes_received': random.randint(500000, 5000000),
                    }
                )
        
        self.stdout.write(self.style.SUCCESS('Sample metrics created'))
        
        # Create sample alerts
        Alert.objects.get_or_create(
            organization=org,
            application=app1,
            alert_type='QUOTA_WARNING',
            severity='WARNING',
            defaults={
                'title': 'Quota Warning',
                'message': f'Application "{app1.name}" has used 80% of allocated quota',
                'data': {'quota_percentage': 80},
                'is_acknowledged': False,
                'is_resolved': False,
            }
        )
        
        Alert.objects.get_or_create(
            organization=org,
            alert_type='THREAT_DETECTED',
            severity='CRITICAL',
            defaults={
                'title': 'Multiple BOLA Attacks Detected',
                'message': 'Detected 15 BOLA (Broken Object Level Authorization) attacks in the last hour',
                'data': {'attack_count': 15, 'attack_type': 'BOLA'},
                'is_acknowledged': False,
                'is_resolved': False,
            }
        )
        
        self.stdout.write(self.style.SUCCESS('Sample alerts created'))
        
        # Create sample API traffic
        self.stdout.write('Creating sample API traffic...')
        environments = Environment.objects.filter(application__in=[app1, app2])
        
        methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        endpoints = [
            '/api/users', '/api/users/{id}', '/api/orders', '/api/orders/{id}',
            '/api/products', '/api/products/{id}', '/api/search', '/api/auth',
            '/api/profile', '/api/settings', '/api/dashboard', '/api/reports'
        ]
        countries = ['US', 'GB', 'DE', 'FR', 'CA', 'AU', 'JP', 'BR', 'IN']
        
        for i in range(100):  # Create 100 sample requests
            env = random.choice(environments)
            timestamp = now - timedelta(minutes=random.randint(0, 1440))  # Last 24 hours
            status_code = random.choices(
                [200, 201, 204, 400, 401, 403, 404, 429, 500, 502],
                weights=[50, 10, 5, 5, 3, 2, 3, 1, 1, 1]
            )[0]
            
            APIRequest.objects.get_or_create(
                request_id=str(uuid.uuid4()),
                defaults={
                    'environment': env,
                    'method': random.choice(methods),
                    'path': random.choice(endpoints).replace('{id}', str(random.randint(1, 1000))),
                    'ip_address': f'{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}',
                    'country_code': random.choice(countries),
                    'status_code': status_code,
                    'response_time_ms': random.randint(20, 500),
                    'is_blocked': status_code == 429 or random.random() < 0.05,
                    'threat_score': random.randint(0, 100) if random.random() < 0.1 else random.randint(0, 30),
                    'timestamp': timestamp,
                    'user_agent': random.choice([
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Mobile App v2.1.0',
                        'Python/3.9 requests',
                        'curl/7.64.1',
                    ])
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Sample API traffic created'))
        
        # Create sample threats
        self.stdout.write('Creating sample threats...')
        threat_types = [
            ('SQL Injection', 'CRITICAL', 'Attempted SQL injection attack detected in authentication endpoint'),
            ('BOLA Attack', 'HIGH', 'Broken Object Level Authorization attack - unauthorized resource access attempt'),
            ('Rate Limit Abuse', 'MEDIUM', 'Excessive requests from single IP address'),
            ('Anomalous Behavior', 'HIGH', 'Unusual access pattern detected from user session'),
            ('XSS Attempt', 'MEDIUM', 'Cross-site scripting attempt in user input'),
        ]
        
        for i, (threat_type, severity, desc) in enumerate(threat_types):
            env = random.choice(environments)
            ThreatDetection.objects.get_or_create(
                environment=env,
                threat_type=threat_type,
                title=f'{threat_type} - {env.application.name}',
                defaults={
                    'severity': severity,
                    'status': random.choice(['OPEN', 'INVESTIGATING', 'RESOLVED']),
                    'description': desc,
                    'ip_address': f'{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}',
                    'affected_endpoint': random.choice(endpoints),
                    'evidence': {
                        'attack_vector': threat_type,
                        'confidence': random.randint(70, 99),
                        'risk_score': random.randint(50, 95),
                    }
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Sample threats created'))
        self.stdout.write(self.style.SUCCESS('\n=== Demo data initialized successfully ==='))
        self.stdout.write(self.style.SUCCESS('\nLogin credentials:'))
        self.stdout.write(self.style.SUCCESS('  Root user: admin@demo.com / admin123'))
        self.stdout.write(self.style.SUCCESS('  Admin user: manager@demo.com / manager123'))
        self.stdout.write(self.style.SUCCESS('  Security user: security@demo.com / security123'))

