"""
Policy models.
Policy engine for custom detection and enforcement rules.
"""

import uuid
from django.db import models
from core.models import Organization, Application, User, TimestampedModel


class Policy(TimestampedModel):
    """
    Security policy with conditions and actions.
    Can be org-level (applies to all apps) or app-specific.
    """
    MODE_CHOICES = [
        ('observe', 'Observe (log only)'),
        ('enforce', 'Enforce (take action)'),
    ]

    policy_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    app = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Null = org-level policy (applies to all apps)"
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Scope
    is_org_level = models.BooleanField(
        default=False,
        help_text="If true, applies to all apps in organization"
    )

    # Condition (DSL as JSON)
    condition = models.JSONField()
    # Example: {
    #   "and": [
    #     {"field": "path_pattern", "op": "eq", "value": "/payments/charge/{id}"},
    #     {"field": "ip_reputation", "op": "eq", "value": "bad"}
    #   ]
    # }

    # Action (JSON)
    action = models.JSONField()
    # Example: {
    #   "type": "block",
    #   "response_code": 403,
    #   "message": "Blocked by security policy"
    # }

    # State
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='observe')
    is_enabled = models.BooleanField(default=False, db_index=True)

    # Simulation
    last_simulation_at = models.DateTimeField(null=True, blank=True)
    last_simulation_result = models.JSONField(null=True, blank=True)
    # Example: {
    #   "affected_requests": 1234,
    #   "would_block": 456,
    #   "date_range": ["2025-11-01", "2025-11-07"]
    # }

    # Priority (lower = higher priority)
    priority = models.IntegerField(default=100, db_index=True)

    # Audit
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_policies'
    )

    class Meta:
        db_table = 'policy'
        verbose_name_plural = 'policies'
        ordering = ['priority', '-created_at']
        indexes = [
            models.Index(fields=['org', 'app', 'is_enabled']),
            models.Index(fields=['org', 'app', 'priority']),
            models.Index(fields=['is_enabled']),
        ]

    def __str__(self):
        scope = "Org-level" if self.is_org_level else f"App: {self.app.name if self.app else 'N/A'}"
        return f"{self.name} ({scope}) - {self.mode}"
