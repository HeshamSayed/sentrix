from django.db import models
from django.contrib.auth import get_user_model
from core.models import BaseModel
import uuid

User = get_user_model()


class APIBehaviorLog(BaseModel):
    """Stores individual API request behavior data for analysis"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255, db_index=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    # Request details
    method = models.CharField(max_length=10)
    endpoint = models.CharField(max_length=255, db_index=True)
    full_path = models.TextField()
    query_params = models.JSONField(default=dict, blank=True)
    
    # Response details
    status_code = models.IntegerField()
    response_time_ms = models.FloatField()
    request_size_bytes = models.IntegerField(default=0)
    response_size_bytes = models.IntegerField(default=0)
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    geo_country = models.CharField(max_length=2, blank=True)
    geo_city = models.CharField(max_length=100, blank=True)
    
    # Authentication
    auth_method = models.CharField(max_length=50, blank=True)
    api_key_id = models.CharField(max_length=255, blank=True)
    
    class Meta:
        db_table = 'security_api_behavior_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['endpoint', 'timestamp']),
        ]


class UserBehaviorBaseline(BaseModel):
    """Stores learned normal behavior patterns for each user"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    endpoint = models.CharField(max_length=255, null=True, blank=True)
    
    # Statistical baselines
    avg_requests_per_hour = models.FloatField(default=0)
    avg_requests_per_day = models.FloatField(default=0)
    avg_response_time_ms = models.FloatField(default=0)
    std_response_time_ms = models.FloatField(default=0)
    
    avg_request_size_bytes = models.FloatField(default=0)
    avg_response_size_bytes = models.FloatField(default=0)
    
    # Common patterns
    common_endpoints = models.JSONField(default=list)
    common_user_agents = models.JSONField(default=list)
    common_countries = models.JSONField(default=list)
    typical_hours = models.JSONField(default=list)  # Active hours (0-23)
    
    # API call sequences
    typical_sequences = models.JSONField(default=list)
    
    # Update metadata
    samples_count = models.IntegerField(default=0)
    last_calculated = models.DateTimeField(auto_now=True)
    baseline_window_days = models.IntegerField(default=7)
    
    class Meta:
        db_table = 'security_user_behavior_baseline'
        unique_together = [['user', 'endpoint']]
        indexes = [
            models.Index(fields=['user', 'last_calculated']),
        ]


class AnomalyDetection(BaseModel):
    """Records detected anomalies in API behavior"""
    
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    ANOMALY_TYPE_CHOICES = [
        ('VELOCITY', 'Velocity Anomaly'),
        ('SEQUENCE', 'Sequence Anomaly'),
        ('DATA', 'Data Anomaly'),
        ('AUTHENTICATION', 'Authentication Anomaly'),
        ('GEOGRAPHIC', 'Geographic Anomaly'),
        ('TIMING', 'Timing Anomaly'),
        ('BOLA', 'BOLA/IDOR Attack'),
        ('SCRAPING', 'Data Scraping'),
        ('ENUMERATION', 'Resource Enumeration'),
    ]
    
    STATUS_CHOICES = [
        ('DETECTED', 'Detected'),
        ('INVESTIGATING', 'Investigating'),
        ('CONFIRMED', 'Confirmed Threat'),
        ('FALSE_POSITIVE', 'False Positive'),
        ('RESOLVED', 'Resolved'),
    ]
    
    # Related entities
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    behavior_log = models.ForeignKey(APIBehaviorLog, on_delete=models.CASCADE, null=True)
    
    # Detection details
    anomaly_type = models.CharField(max_length=50, choices=ANOMALY_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, db_index=True)
    confidence_score = models.FloatField()  # 0.0 to 1.0
    risk_score = models.FloatField()  # 0.0 to 100.0
    
    # Description
    title = models.CharField(max_length=255)
    description = models.TextField()
    indicators = models.JSONField(default=dict)  # Detailed anomaly indicators
    
    # Context
    ip_address = models.GenericIPAddressField()
    endpoint = models.CharField(max_length=255)
    timestamp = models.DateTimeField(db_index=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DETECTED')
    investigated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='investigated_anomalies'
    )
    investigated_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'security_anomaly_detection'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['severity', 'status', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['anomaly_type', 'timestamp']),
        ]


class ThreatResponse(BaseModel):
    """Records automated responses to detected threats"""
    
    ACTION_CHOICES = [
        ('LOG', 'Log Only'),
        ('ALERT', 'Alert Security Team'),
        ('RATE_LIMIT', 'Apply Rate Limiting'),
        ('THROTTLE', 'Throttle Requests'),
        ('CHALLENGE', 'Challenge with CAPTCHA'),
        ('BLOCK_TEMPORARY', 'Temporary Block'),
        ('BLOCK_PERMANENT', 'Permanent Block'),
    ]
    
    anomaly = models.ForeignKey(AnomalyDetection, on_delete=models.CASCADE)
    action_taken = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    # Action details
    duration_minutes = models.IntegerField(null=True, blank=True)  # For temporary actions
    parameters = models.JSONField(default=dict)  # Action-specific parameters
    
    # Result
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    # Metadata
    executed_at = models.DateTimeField(auto_now_add=True)
    executed_by_system = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'security_threat_response'
        ordering = ['-executed_at']


class SecurityConfiguration(BaseModel):
    """Global configuration for behavioral security system"""
    
    # Detection thresholds
    velocity_threshold_multiplier = models.FloatField(default=3.0)
    anomaly_score_threshold = models.FloatField(default=0.75)
    min_requests_for_baseline = models.IntegerField(default=100)
    baseline_window_days = models.IntegerField(default=7)
    
    # Response configuration
    auto_block_enabled = models.BooleanField(default=False)
    auto_rate_limit_enabled = models.BooleanField(default=True)
    block_duration_minutes = models.IntegerField(default=60)
    
    # Alert configuration
    alert_on_severity = models.JSONField(default=list)  # ['HIGH', 'CRITICAL']
    alert_channels = models.JSONField(default=list)  # ['email', 'slack']
    
    # ML configuration
    model_update_frequency_minutes = models.IntegerField(default=15)
    feature_importance_threshold = models.FloatField(default=0.05)
    false_positive_tolerance = models.FloatField(default=0.01)
    
    # System metadata
    is_active = models.BooleanField(default=True)
    last_updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'security_configuration'
        verbose_name = 'Security Configuration'
        verbose_name_plural = 'Security Configuration'


class BlockedEntity(BaseModel):
    """Tracks blocked IPs, users, or API keys"""
    
    ENTITY_TYPE_CHOICES = [
        ('IP', 'IP Address'),
        ('USER', 'User'),
        ('API_KEY', 'API Key'),
        ('SESSION', 'Session ID'),
    ]
    
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPE_CHOICES)
    entity_value = models.CharField(max_length=255, db_index=True)
    
    # Block details
    reason = models.TextField()
    blocked_at = models.DateTimeField(auto_now_add=True)
    blocked_until = models.DateTimeField(null=True, blank=True)
    is_permanent = models.BooleanField(default=False)
    
    # Related anomaly
    anomaly = models.ForeignKey(AnomalyDetection, on_delete=models.SET_NULL, null=True)
    
    # Metadata
    blocked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    unblocked_at = models.DateTimeField(null=True, blank=True)
    unblocked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='unblocked_entities'
    )
    
    class Meta:
        db_table = 'security_blocked_entity'
        ordering = ['-blocked_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_value', 'blocked_until']),
        ]

