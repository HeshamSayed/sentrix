from django.db import models
from core.models import BaseModel

class MetricSnapshot(BaseModel):
    """Time-series metrics for dashboards"""
    
    GRANULARITY_CHOICES = [
        ('MINUTE', 'Per Minute'),
        ('HOUR', 'Per Hour'),
        ('DAY', 'Per Day'),
    ]
    
    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.CASCADE,
        related_name='metrics',
        null=True,
        blank=True
    )
    
    environment = models.ForeignKey(
        'applications.Environment',
        on_delete=models.CASCADE,
        related_name='metrics',
        null=True,
        blank=True
    )
    
    timestamp = models.DateTimeField(db_index=True)
    granularity = models.CharField(max_length=20, choices=GRANULARITY_CHOICES)
    
    # Traffic metrics
    total_requests = models.BigIntegerField(default=0)
    successful_requests = models.BigIntegerField(default=0)
    failed_requests = models.BigIntegerField(default=0)
    blocked_requests = models.BigIntegerField(default=0)
    
    # Performance metrics
    avg_response_time_ms = models.FloatField(default=0)
    p95_response_time_ms = models.FloatField(default=0)
    p99_response_time_ms = models.FloatField(default=0)
    
    # Security metrics
    threat_count = models.IntegerField(default=0)
    high_risk_requests = models.IntegerField(default=0)
    
    # Unique metrics
    unique_ips = models.IntegerField(default=0)
    unique_endpoints = models.IntegerField(default=0)
    
    # Data transfer
    bytes_sent = models.BigIntegerField(default=0)
    bytes_received = models.BigIntegerField(default=0)
    
    class Meta:
        db_table = 'metric_snapshots'
        unique_together = [['application', 'environment', 'timestamp', 'granularity']]
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['application', 'granularity', '-timestamp']),
            models.Index(fields=['environment', 'granularity', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.granularity}"

class Alert(BaseModel):
    """System alerts and notifications"""
    
    ALERT_TYPE_CHOICES = [
        ('QUOTA_WARNING', 'Quota Warning'),
        ('QUOTA_EXCEEDED', 'Quota Exceeded'),
        ('THREAT_DETECTED', 'Threat Detected'),
        ('ANOMALY_DETECTED', 'Anomaly Detected'),
        ('SERVICE_DOWN', 'Service Down'),
        ('HIGH_ERROR_RATE', 'High Error Rate'),
    ]
    
    SEVERITY_CHOICES = [
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    
    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.CASCADE,
        related_name='alerts',
        null=True,
        blank=True
    )
    
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Alert data
    data = models.JSONField(default=dict, blank=True)
    
    # Status
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'is_resolved', '-created_at']),
            models.Index(fields=['severity', 'is_resolved', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.severity} - {self.title}"

class Dashboard(BaseModel):
    """Custom dashboards for users"""
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='dashboards'
    )
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Dashboard configuration
    layout = models.JSONField(default=dict)  # Widget positions and configurations
    is_default = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'dashboards'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.user.email} - {self.name}"

