from django.db import models
from core.models import BaseModel

class Organization(BaseModel):
    """Organization/Tenant model"""
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    
    # Subscription and licensing
    subscription_tier = models.CharField(
        max_length=50,
        choices=[
            ('TRIAL', 'Trial'),
            ('STARTER', 'Starter'),
            ('PROFESSIONAL', 'Professional'),
            ('ENTERPRISE', 'Enterprise'),
        ],
        default='TRIAL'
    )
    is_active = models.BooleanField(default=True)
    subscription_starts_at = models.DateTimeField(null=True, blank=True)
    subscription_ends_at = models.DateTimeField(null=True, blank=True)
    
    # Account limits
    max_users = models.IntegerField(default=30)
    current_users = models.IntegerField(default=0)
    
    # Global quota (in millions of API calls per month)
    global_quota = models.BigIntegerField(default=1000000)  # 1M calls
    used_quota = models.BigIntegerField(default=0)
    
    # Billing
    billing_email = models.EmailField()
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Settings
    settings = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'organizations'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def quota_percentage(self):
        """Calculate quota usage percentage"""
        if self.global_quota == 0:
            return 0
        return (self.used_quota / self.global_quota) * 100
    
    @property
    def remaining_quota(self):
        """Calculate remaining quota"""
        return max(0, self.global_quota - self.used_quota)
    
    @property
    def can_add_user(self):
        """Check if organization can add more users"""
        return self.current_users < self.max_users

class OrganizationInvite(BaseModel):
    """Invitation for users to join an organization"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='invites')
    email = models.EmailField()
    role = models.CharField(
        max_length=50,
        choices=[
            ('ADMIN', 'Admin'),
            ('SECURITY', 'Security'),
        ],
        default='SECURITY'
    )
    token = models.CharField(max_length=255, unique=True)
    invited_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='sent_invites')
    accepted = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'organization_invites'
        unique_together = [['organization', 'email']]
    
    def __str__(self):
        return f"{self.email} -> {self.organization.name}"

