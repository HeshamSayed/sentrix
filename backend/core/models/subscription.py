"""
Subscription and billing models for SENTRIX onboarding
"""

from django.db import models
from django.contrib.auth import get_user_model
from core.models import BaseModel

User = get_user_model()


class SubscriptionPlan(BaseModel):
    """Subscription plans available for customers"""
    
    PLAN_TYPES = [
        ('free', 'Free'),
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, unique=True)
    description = models.TextField()
    
    # Pricing
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    annual_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Quotas and limits
    max_requests_per_month = models.IntegerField(help_text="Maximum API requests per month")
    max_applications = models.IntegerField(help_text="Maximum number of applications")
    max_users = models.IntegerField(help_text="Maximum team members")
    max_environments = models.IntegerField(default=3)
    
    # Features
    behavioral_analysis = models.BooleanField(default=True)
    real_time_blocking = models.BooleanField(default=True)
    advanced_analytics = models.BooleanField(default=False)
    custom_rules = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    dedicated_resources = models.BooleanField(default=False)
    sla_guarantee = models.BooleanField(default=False)
    
    # Availability
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True, help_text="Show in pricing page")
    
    class Meta:
        db_table = 'subscription_plans'
        ordering = ['monthly_price']
    
    def __str__(self):
        return f"{self.name} (${self.monthly_price}/mo)"


class Subscription(BaseModel):
    """Customer subscription"""
    
    STATUS_CHOICES = [
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('expired', 'Expired'),
    ]
    
    BILLING_CYCLE = [
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    ]
    
    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE, default='monthly')
    
    # Trial period
    trial_start_date = models.DateTimeField(null=True, blank=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    
    # Subscription period
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    
    # Usage tracking
    current_period_requests = models.IntegerField(default=0)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    
    # Billing
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    last_payment_date = models.DateTimeField(null=True, blank=True)
    next_payment_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'subscriptions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.organization.name} - {self.plan.name} ({self.status})"
    
    def is_trial(self):
        """Check if subscription is in trial period"""
        return self.status == 'trial'
    
    def is_active(self):
        """Check if subscription is active"""
        return self.status == 'active'
    
    def has_quota_remaining(self):
        """Check if organization has quota remaining"""
        return self.current_period_requests < self.plan.max_requests_per_month


class OnboardingSession(BaseModel):
    """Track onboarding progress for new users"""
    
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('organization_created', 'Organization Created'),
        ('application_created', 'Application Created'),
        ('integration_tested', 'Integration Tested'),
        ('completed', 'Completed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='onboarding_sessions')
    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='onboarding_sessions'
    )
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='started')
    
    # Onboarding data
    company_name = models.CharField(max_length=255, blank=True)
    company_size = models.CharField(max_length=50, blank=True)
    use_case = models.TextField(blank=True)
    target_url = models.URLField(blank=True)
    
    # Progress tracking
    step_completed = models.JSONField(default=dict)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'onboarding_sessions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.status}"

