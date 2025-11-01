"""
Restructured models for proper Organization → Environment → Application hierarchy
Each organization can have multiple environments
Each environment can have multiple applications
Each application has its own secure API key
"""

from django.db import models
from core.models import BaseModel
import secrets
import string


def generate_api_key():
    """Generate a secure API key"""
    prefix = "sentrix_live_"
    key_length = 32
    characters = string.ascii_letters + string.digits
    key = ''.join(secrets.choice(characters) for _ in range(key_length))
    return f"{prefix}{key}"


class Environment(BaseModel):
    """
    Environment under an organization (Production, Staging, Development, etc.)
    An organization can have multiple environments
    """
    
    ENV_TYPES = [
        ('development', 'Development'),
        ('staging', 'Staging'),
        ('production', 'Production'),
        ('testing', 'Testing'),
        ('custom', 'Custom'),
    ]
    
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='environments'
    )
    
    name = models.CharField(max_length=100)  # e.g., "Production", "Staging"
    environment_type = models.CharField(max_length=50, choices=ENV_TYPES, default='production')
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    
    # Environment-level settings
    is_active = models.BooleanField(default=True)
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True)
    
    # Resource allocation for this environment
    max_applications = models.IntegerField(default=10)
    allocated_quota = models.BigIntegerField(default=1000000)  # Requests per month
    
    # Environment variables (encrypted)
    env_variables = models.JSONField(default=dict, blank=True)
    
    # Settings
    settings = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'environments'
        unique_together = [['organization', 'slug']]
        ordering = ['environment_type', 'name']
    
    def __str__(self):
        return f"{self.organization.name} - {self.name}"
    
    @property
    def total_applications(self):
        """Get total number of applications in this environment"""
        return self.applications.count()
    
    @property
    def active_applications(self):
        """Get active applications"""
        return self.applications.filter(is_active=True).count()


class Application(BaseModel):
    """
    Application/Service under an environment
    Each application has its own unique API key for secure access
    """
    
    environment = models.ForeignKey(
        Environment,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    
    name = models.CharField(max_length=255)  # e.g., "TODO App Production"
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)
    
    # Secure API Key (unique per application)
    api_key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        default=generate_api_key
    )
    
    # Target backend URL (where SENTRIX Edge proxies requests to)
    base_url = models.URLField(max_length=500)  # e.g., "https://todo.com", "https://api.todo.com"
    target_url = models.URLField(max_length=500)  # Full target URL

    # Traffic mode: header (API key) vs DNS (host-based)
    TRAFFIC_MODE_CHOICES = [
        ("api_key", "API Key Header"),
        ("dns", "DNS / Host-based"),
    ]
    traffic_mode = models.CharField(max_length=20, choices=TRAFFIC_MODE_CHOICES, default="api_key")

    # DNS onboarding fields (for zero-deploy protection)
    protected_domain = models.CharField(
        max_length=255,
        blank=True,
        help_text="Customer domain protected via SENTRIX (e.g., api.x.com)"
    )
    edge_hostname = models.CharField(
        max_length=255,
        blank=True,
        help_text="Assigned SENTRIX edge hostname (e.g., c-<id>.edge.sentrix.io)"
    )
    dns_verification_token = models.CharField(
        max_length=255,
        blank=True,
        help_text="Token used for DNS TXT verification (_sentrix-verify.<domain>)"
    )
    DNS_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("failed", "Failed"),
    ]
    dns_status = models.CharField(max_length=20, choices=DNS_STATUS_CHOICES, default="pending")
    
    # Failover & bypass
    bypass_token = models.CharField(
        max_length=255,
        blank=True,
        help_text="Emergency bypass token (if SENTRIX down, origin accepts this in X-SENTRIX-Bypass header)"
    )
    origin_signature_key = models.CharField(
        max_length=255,
        blank=True,
        help_text="Secret key for signing proxied requests (X-SENTRIX-Signature header)"
    )
    
    # Application status
    is_active = models.BooleanField(default=True)
    is_traffic_enabled = models.BooleanField(default=True)
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True)
    
    # Quota management (allocated from environment's quota)
    allocated_quota = models.BigIntegerField(default=100000)  # Requests per month
    used_quota = models.BigIntegerField(default=0)
    
    # Security settings
    rate_limit_per_minute = models.IntegerField(default=1000)
    rate_limit_per_hour = models.IntegerField(default=10000)
    rate_limit_per_day = models.IntegerField(default=100000)
    
    # IP filtering
    blocked_ips = models.JSONField(default=list, blank=True)
    allowed_ips = models.JSONField(default=list, blank=True)  # Empty = all allowed
    
    # Geo-blocking
    blocked_countries = models.JSONField(default=list, blank=True)  # ISO codes
    allowed_countries = models.JSONField(default=list, blank=True)  # Empty = all allowed
    
    # Headers
    custom_headers = models.JSONField(default=dict, blank=True)  # Headers to add to proxied requests
    
    # Webhooks
    webhook_url = models.URLField(blank=True, null=True)  # Notify on security events
    
    # Settings
    settings = models.JSONField(default=dict, blank=True)
    
    # Metadata
    framework = models.CharField(max_length=100, blank=True)  # e.g., "Django", "Flask", "Express"
    language = models.CharField(max_length=50, blank=True)  # e.g., "Python", "JavaScript"
    
    class Meta:
        db_table = 'applications'
        unique_together = [['environment', 'slug']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['api_key']),
            models.Index(fields=['environment', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.environment.organization.name} - {self.environment.name} - {self.name}"
    
    @property
    def organization(self):
        """Quick access to parent organization"""
        return self.environment.organization
    
    @property
    def quota_percentage(self):
        """Calculate quota usage percentage"""
        if self.allocated_quota == 0:
            return 0
        return (self.used_quota / self.allocated_quota) * 100
    
    @property
    def remaining_quota(self):
        """Calculate remaining quota"""
        return max(0, self.allocated_quota - self.used_quota)
    
    @property
    def is_quota_exceeded(self):
        """Check if quota is exceeded"""
        return self.used_quota >= self.allocated_quota
    
    def regenerate_api_key(self):
        """Generate a new API key"""
        self.api_key = generate_api_key()
        self.save(update_fields=['api_key', 'updated_at'])
        return self.api_key


class APIEndpoint(BaseModel):
    """Discovered API endpoints for an application"""
    
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='discovered_endpoints'
    )
    
    method = models.CharField(max_length=10)  # GET, POST, PUT, DELETE, etc.
    path = models.TextField()
    path_pattern = models.TextField()  # Normalized path with params
    
    # Discovery metadata
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    
    # Traffic stats
    request_count = models.BigIntegerField(default=0)
    error_count = models.BigIntegerField(default=0)
    avg_response_time = models.FloatField(default=0)  # milliseconds
    
    # Security classification
    is_sensitive = models.BooleanField(default=False)
    risk_score = models.IntegerField(default=0)  # 0-100
    
    # OWASP API Security Top 10 risks
    security_issues = models.JSONField(default=list, blank=True)
    
    # Parameters
    query_params = models.JSONField(default=list, blank=True)
    body_params = models.JSONField(default=list, blank=True)
    headers = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = 'api_endpoints'
        unique_together = [['application', 'method', 'path_pattern']]
        ordering = ['-request_count']
    
    def __str__(self):
        return f"{self.method} {self.path_pattern}"


class QuotaTransfer(BaseModel):
    """Track quota transfers between applications or environments"""
    
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='quota_transfers'
    )
    
    from_application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='quota_transfers_out',
        null=True,
        blank=True
    )
    
    to_application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='quota_transfers_in'
    )
    
    amount = models.BigIntegerField()
    reason = models.TextField(blank=True)
    
    performed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='quota_transfers'
    )
    
    class Meta:
        db_table = 'quota_transfers'
        ordering = ['-created_at']
    
    def __str__(self):
        source = self.from_application.name if self.from_application else "Global Pool"
        return f"{source} -> {self.to_application.name}: {self.amount}"

