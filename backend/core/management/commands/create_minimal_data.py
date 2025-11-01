from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from organizations.models import Organization


class Command(BaseCommand):
    help = 'Create minimal test data - only organization and user, no apps/metrics/traffic'

    def handle(self, *args, **options):
        self.stdout.write('Creating minimal test data...')
        
        # Create organization
        org, created = Organization.objects.get_or_create(
            slug='test-org',
            defaults={
                'name': 'Test Organization',
                'billing_email': 'test@test.com',
                'subscription_tier': 'TRIAL',
                'global_quota': 1000000,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created organization: {org.name}'))
        else:
            self.stdout.write(f'✓ Organization exists: {org.name}')
        
        # Create user
        User = get_user_model()
        user, created = User.objects.get_or_create(
            email='test@test.com',
            defaults={
                'first_name': 'Test',
                'last_name': 'User',
                'role': 'ROOT',
                'organization': org,
            }
        )
        
        if created:
            user.set_password('test123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Created user: {user.email}'))
        else:
            user.set_password('test123')
            user.save()
            self.stdout.write(f'✓ User exists: {user.email}')
        
        self.stdout.write(self.style.SUCCESS('\n=== Minimal test data created ==='))
        self.stdout.write('Database contains:')
        self.stdout.write('  - 1 Organization')
        self.stdout.write('  - 1 User')
        self.stdout.write('  - 0 Applications ❌')
        self.stdout.write('  - 0 Environments ❌')
        self.stdout.write('  - 0 Metrics ❌')
        self.stdout.write('  - 0 Traffic Logs ❌')
        self.stdout.write('  - 0 Threats ❌')
        self.stdout.write('  - 0 Alerts ❌')
        self.stdout.write('\nLogin: test@test.com / test123')

