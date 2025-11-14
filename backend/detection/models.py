"""
Detection models.
Stores threat detections and alerts.
"""

import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField
from core.models import Organization, Application, APIEndpoint, User, TimestampedModel


class DetectionEvent(TimestampedModel):
    """
    Security detection/alert.
    Isolated per application.
    """
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('investigating', 'Investigating'),
        ('confirmed', 'Confirmed'),
        ('false_positive', 'False Positive'),
        ('resolved', 'Resolved'),
    ]

    DETECTOR_TYPES = [
        ('rule_based', 'Rule-based'),
        ('statistical', 'Statistical'),
        ('r1_realtime', 'R1 Real-time'),
        ('r1_batch', 'R1 Batch'),
    ]

    detection_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    app = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='detections'
    )
    endpoint = models.ForeignKey(
        APIEndpoint,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Related events (from api_request_event table)
    trigger_event_ids = ArrayField(
        models.BigIntegerField(),
        default=list,
        help_text="Event IDs that triggered this detection"
    )
    trace_ids = ArrayField(
        models.CharField(max_length=100),
        default=list,
        help_text="Trace IDs for investigation"
    )

    # Detection metadata
    detector_type = models.CharField(max_length=20, choices=DETECTOR_TYPES)
    detector_name = models.CharField(max_length=100, db_index=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, db_index=True)

    # Scores
    confidence_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        help_text="Confidence score 0.0 to 1.0"
    )
    r1_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Deepseek-R1 risk score 0.0 to 1.0"
    )

    # Deepseek-R1 explanation (JSONB)
    r1_explanation = models.JSONField(null=True, blank=True)
    # Example: {"reasoning": "...", "evidence": [...], "model_version": "r1-distill-v1"}

    # Attack classification
    attack_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g., sqli, xss, credential_stuffing, data_exfil, business_logic_abuse"
    )
    client_ip = models.GenericIPAddressField(null=True, blank=True)

    # Lifecycle
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_detections'
    )

    detected_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'detection_event'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['org', 'app', 'detected_at']),
            models.Index(fields=['org', 'app', 'severity', 'status']),
            models.Index(fields=['status', 'detected_at']),
            models.Index(fields=['detector_name']),
        ]

    def __str__(self):
        return f"{self.severity.upper()} - {self.detector_name} ({self.app.name})"
