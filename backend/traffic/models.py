from django.db import models
from core.models import BaseModel

class APIRequest(BaseModel):
    """Individual API request log (sampled for storage efficiency)"""
    environment = models.ForeignKey(
        'applications.Environment',
        on_delete=models.CASCADE,
        related_name='api_requests'
    )
    
    # Request details
    method = models.CharField(max_length=10)
    path = models.TextField()
    query_params = models.JSONField(default=dict, blank=True)
    
    # Client info
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    
    # Response
    status_code = models.IntegerField()
    response_time_ms = models.IntegerField()  # milliseconds
    
    # Security
    is_blocked = models.BooleanField(default=False)
    block_reason = models.CharField(max_length=255, blank=True)
    
    # Threat detection
    threat_score = models.IntegerField(default=0)  # 0-100
    threat_indicators = models.JSONField(default=list, blank=True)
    
    # Metadata
    request_id = models.CharField(max_length=255, unique=True)
    timestamp = models.DateTimeField(db_index=True)
    
    class Meta:
        db_table = 'api_requests'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['environment', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
            models.Index(fields=['threat_score', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.method} {self.path} - {self.status_code}"

class ThreatDetection(BaseModel):
    """Detected security threats and anomalies"""
    
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('INVESTIGATING', 'Investigating'),
        ('RESOLVED', 'Resolved'),
        ('FALSE_POSITIVE', 'False Positive'),
    ]
    
    environment = models.ForeignKey(
        'applications.Environment',
        on_delete=models.CASCADE,
        related_name='threats'
    )
    
    # Threat classification
    threat_type = models.CharField(max_length=100)  # BOLA, Rate Limit, Injection, etc.
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='OPEN')
    
    # Details
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Related data
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    affected_endpoint = models.TextField(blank=True)
    
    # Evidence
    evidence = models.JSONField(default=dict, blank=True)
    related_requests = models.ManyToManyField(APIRequest, related_name='threats', blank=True)
    
    # Resolution
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_threats'
    )
    resolution_notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'threat_detections'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['environment', 'status', '-created_at']),
            models.Index(fields=['severity', 'status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.severity} - {self.title}"

class BlockedIP(BaseModel):
    """IPs that have been blocked"""
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='blocked_ips'
    )
    
    ip_address = models.GenericIPAddressField()
    reason = models.TextField()
    
    # Scope
    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='blocked_ip_records'
    )
    
    # Auto-unblock
    expires_at = models.DateTimeField(null=True, blank=True)
    
    blocked_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='blocked_ips'
    )
    
    class Meta:
        db_table = 'blocked_ips'
        unique_together = [['organization', 'ip_address']]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.ip_address} - {self.reason}"

class RateLimitRule(BaseModel):
    """Rate limiting rules"""
    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.CASCADE,
        related_name='rate_limit_rules'
    )
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Rule definition
    path_pattern = models.CharField(max_length=500)  # Can use wildcards
    max_requests = models.IntegerField()
    time_window_seconds = models.IntegerField()
    
    # Scope
    applies_to = models.CharField(
        max_length=50,
        choices=[
            ('IP', 'Per IP Address'),
            ('USER', 'Per User'),
            ('GLOBAL', 'Global'),
        ],
        default='IP'
    )
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'rate_limit_rules'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.max_requests}/{self.time_window_seconds}s"

