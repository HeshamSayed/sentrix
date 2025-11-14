"""
Core models for Sentrix multi-tenant architecture.

Hierarchy:
- Organization (tenant)
- Subscription (plan + quotas)
- User (licensed seats)
- Application (api domains, isolated data)
"""

import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.utils import timezone


class TimestampedModel(models.Model):
    """Abstract base model with created_at and updated_at"""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Organization(TimestampedModel):
    """
    Root tenant entity.
    All data is scoped to an organization.
    """
    org_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    # Default configuration inherited by all applications
    default_config = models.JSONField(default=dict, blank=True)
    # Example: {"rate_limit_rpm": 1000, "enable_r1_realtime": true, ...}

    class Meta:
        db_table = 'organization'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def get_active_subscription(self):
        """Get current active subscription"""
        return self.subscriptions.filter(
            is_active=True,
            valid_from__lte=timezone.now()
        ).exclude(
            valid_until__lt=timezone.now()
        ).order_by('-created_at').first()


class Subscription(TimestampedModel):
    """
    Subscription plan with quotas and feature flags.
    Each organization has one active subscription at a time.
    """
    PLAN_TIERS = [
        ('free', 'Free'),
        ('pro', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]

    subscription_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan_tier = models.CharField(max_length=20, choices=PLAN_TIERS, default='free')

    # Quotas
    quota_max_applications = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Maximum number of applications allowed"
    )
    quota_max_users = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        help_text="Maximum number of licensed user seats"
    )
    quota_requests_per_month = models.BigIntegerField(
        default=1_000_000,
        validators=[MinValueValidator(1)],
        help_text="Maximum API requests per month across all apps"
    )

    # Feature flags (JSONB)
    features = models.JSONField(default=dict, blank=True)
    # Example: {"r1_realtime": true, "threat_hunting": true, "shift_left": false}

    # Validity period
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'subscription'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['org', 'is_active']),
            models.Index(fields=['org', 'valid_from', 'valid_until']),
        ]

    def __str__(self):
        return f"{self.org.name} - {self.plan_tier} ({self.subscription_id})"

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled in this plan"""
        return self.features.get(feature_name, False)

    def has_app_quota(self) -> bool:
        """Check if org can create more applications"""
        current_count = self.org.applications.filter(is_active=True).count()
        return current_count < self.quota_max_applications

    def has_user_quota(self) -> bool:
        """Check if org can create more users"""
        current_count = self.org.users.filter(is_active=True).count()
        return current_count < self.quota_max_users


class User(TimestampedModel):
    """
    User account (licensed seat).
    Scoped to an organization.
    """
    ROLES = [
        ('admin', 'Administrator'),
        ('analyst', 'Security Analyst'),
        ('viewer', 'Viewer'),
    ]

    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='users'
    )

    email = models.EmailField(unique=True, db_index=True)
    password_hash = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255, blank=True)

    role = models.CharField(max_length=20, choices=ROLES, default='viewer')
    is_active = models.BooleanField(default=True, db_index=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'sentrix_user'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['org', 'is_active']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.email} ({self.org.name})"

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        from core.permissions import PERMISSIONS
        allowed = PERMISSIONS.get(self.role, [])
        return '*' in allowed or permission in allowed


class Application(TimestampedModel):
    """
    Application entity.
    Each application represents a protected API domain.
    Data (events, endpoints, detections) is isolated per application.
    """
    FAILOVER_MODES = [
        ('fail_open', 'Fail Open (forward to origin on error)'),
        ('fail_closed', 'Fail Closed (block on error)'),
    ]

    app_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='applications'
    )

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)

    # DNS & Origin
    domain = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Customer domain (e.g., api.customer-payments.com)"
    )
    origin_url = models.URLField(
        max_length=500,
        help_text="Backend origin URL (e.g., https://origin.customer.com)"
    )
    cname_target = models.CharField(
        max_length=255,
        help_text="Sentrix edge CNAME target (e.g., sentrix-edge-us-east.example.com)"
    )

    # DNS Verification
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False)
    dns_verified = models.BooleanField(default=False, db_index=True)
    dns_verified_at = models.DateTimeField(null=True, blank=True)

    # Configuration (overrides org.default_config)
    custom_config = models.JSONField(default=dict, blank=True)
    # Merged config = org.default_config + custom_config

    # Failover behavior
    failover_mode = models.CharField(
        max_length=20,
        choices=FAILOVER_MODES,
        default='fail_open'
    )

    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'application'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['org', 'slug'],
                name='unique_org_slug'
            )
        ]
        indexes = [
            models.Index(fields=['org', 'is_active']),
            models.Index(fields=['domain']),
        ]

    def __str__(self):
        return f"{self.name} - {self.domain} ({self.org.name})"

    def get_merged_config(self) -> dict:
        """
        Get merged configuration (org defaults + app overrides).
        This should be cached in Redis in production.
        """
        merged = {**self.org.default_config, **self.custom_config}
        return merged


class APIEndpoint(TimestampedModel):
    """
    Discovered API endpoint (catalog).
    Isolated per application.
    """
    endpoint_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    app = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='endpoints'
    )

    method = models.CharField(max_length=10, db_index=True)  # GET, POST, etc.
    path_pattern = models.CharField(
        max_length=500,
        db_index=True,
        help_text="Canonicalized path (e.g., /payments/charge/{id})"
    )

    # Inferred schemas
    request_schema = models.JSONField(null=True, blank=True)
    response_schema = models.JSONField(null=True, blank=True)

    # Metadata
    owner = models.CharField(max_length=255, blank=True)
    tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    risk_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.5,
        help_text="Risk score 0.0 to 1.0"
    )

    # Stats
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now_add=True)
    request_count = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'api_endpoint'
        ordering = ['-last_seen']
        constraints = [
            models.UniqueConstraint(
                fields=['org', 'app', 'method', 'path_pattern'],
                name='unique_endpoint'
            )
        ]
        indexes = [
            models.Index(fields=['org', 'app']),
            models.Index(fields=['path_pattern']),
            models.Index(fields=['last_seen']),
        ]

    def __str__(self):
        return f"{self.method} {self.path_pattern} ({self.app.name})"


class AuditLog(models.Model):
    """
    Immutable audit log for all sensitive actions.
    """
    audit_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    app = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    actor_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    action = models.CharField(max_length=100, db_index=True)
    # Examples: policy.created, policy.enabled, user.invited, config.updated

    resource_type = models.CharField(max_length=50, db_index=True)
    resource_id = models.CharField(max_length=100, blank=True)

    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'audit_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['org', 'timestamp']),
            models.Index(fields=['actor_user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.action} by {self.actor_user} at {self.timestamp}"


class UsageTracking(TimestampedModel):
    """
    Track usage per org/app for quota enforcement.
    Aggregated periodically (daily/monthly).
    """
    usage_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    app = models.ForeignKey(Application, on_delete=models.CASCADE)

    period_start = models.DateTimeField(db_index=True)
    period_end = models.DateTimeField(db_index=True)

    request_count = models.BigIntegerField(default=0)
    blocked_count = models.BigIntegerField(default=0)
    r1_invocation_count = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'usage_tracking'
        ordering = ['-period_start']
        constraints = [
            models.UniqueConstraint(
                fields=['org', 'app', 'period_start'],
                name='unique_usage_period'
            )
        ]
        indexes = [
            models.Index(fields=['org', 'period_start']),
            models.Index(fields=['app', 'period_start']),
        ]

    def __str__(self):
        return f"{self.org.name} - {self.app.name} ({self.period_start} to {self.period_end})"
