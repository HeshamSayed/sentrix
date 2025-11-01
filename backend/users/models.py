from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from core.models import BaseModel
import uuid

class UserManager(BaseUserManager):
    """Custom user manager"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ROOT')
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """Custom user model with organization and role-based access"""
    
    ROLE_CHOICES = [
        ('ROOT', 'Root User'),
        ('ADMIN', 'Admin'),
        ('SECURITY', 'Security User'),
    ]
    
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True
    )
    
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='SECURITY')
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_licensed = models.BooleanField(default=True)
    
    # Permissions (for granular control)
    permissions = models.JSONField(default=dict, blank=True)
    
    # Metadata
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    login_count = models.IntegerField(default=0)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email
    
    @property
    def is_root(self):
        return self.role == 'ROOT'
    
    @property
    def is_admin(self):
        return self.role in ['ROOT', 'ADMIN']
    
    @property
    def can_manage_users(self):
        return self.role in ['ROOT', 'ADMIN']
    
    def has_permission(self, permission_key):
        """
        Check if user has a specific permission
        Checks both role-based and custom permissions
        """
        if self.is_root:
            return True  # Root has all permissions
        
        # Check custom permissions first (user-specific overrides)
        if permission_key in self.permissions:
            return self.permissions[permission_key]
        
        # Fall back to role-based default permissions
        from .permissions_models import DEFAULT_ROLE_PERMISSIONS
        role_permissions = DEFAULT_ROLE_PERMISSIONS.get(self.role, [])
        return permission_key in role_permissions
    
    def get_all_permissions(self):
        """
        Get all permissions for this user
        Returns a dict with permission keys as keys and boolean values
        """
        from .permissions_models import DEFAULT_ROLE_PERMISSIONS, DEFAULT_PERMISSIONS
        
        if self.is_root:
            # Root has all permissions
            return {perm[0]: True for perm in DEFAULT_PERMISSIONS}
        
        # Start with role-based permissions
        role_permissions = DEFAULT_ROLE_PERMISSIONS.get(self.role, [])
        all_perms = {perm: True for perm in role_permissions}
        
        # Apply custom overrides
        if self.permissions:
            all_perms.update(self.permissions)
        
        return all_perms

class APIKey(BaseModel):
    """API Keys for programmatic access"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=255)
    key = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Rate limiting
    rate_limit = models.IntegerField(default=1000)  # requests per hour
    
    class Meta:
        db_table = 'api_keys'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.user.email})"

class AuditLog(BaseModel):
    """Audit log for tracking all user actions"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='audit_logs', null=True)
    
    action = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=255, null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    details = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.resource_type}"

