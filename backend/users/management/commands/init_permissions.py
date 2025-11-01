"""
Management command to initialize default permissions
"""
from django.core.management.base import BaseCommand
from users.permissions_models import (
    Permission, RolePermission,
    DEFAULT_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS
)


class Command(BaseCommand):
    help = 'Initialize default permissions and role permissions'

    def handle(self, *args, **kwargs):
        self.stdout.write('Initializing permissions...')
        
        created_count = 0
        updated_count = 0
        
        # Create/update permissions
        for code, name, description, category in DEFAULT_PERMISSIONS:
            permission, created = Permission.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'description': description,
                    'category': category,
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ Created permission: {code}')
            else:
                # Update existing
                permission.name = name
                permission.description = description
                permission.category = category
                permission.save()
                updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Permissions initialized: {created_count} created, {updated_count} updated'
            )
        )
        
        # Create role permissions
        self.stdout.write('\nInitializing role permissions...')
        role_perm_count = 0
        
        for role, permission_codes in DEFAULT_ROLE_PERMISSIONS.items():
            for code in permission_codes:
                try:
                    permission = Permission.objects.get(code=code)
                    role_perm, created = RolePermission.objects.get_or_create(
                        role=role,
                        permission=permission,
                        defaults={'is_default': True}
                    )
                    if created:
                        role_perm_count += 1
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠ Permission {code} not found for role {role}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Role permissions initialized: {role_perm_count} created'
            )
        )
        
        self.stdout.write(self.style.SUCCESS('\n✅ All permissions initialized successfully!'))

