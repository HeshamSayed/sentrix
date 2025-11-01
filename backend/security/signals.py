"""
Django signals for security events
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AnomalyDetection, ThreatResponse


@receiver(post_save, sender=AnomalyDetection)
def on_anomaly_detected(sender, instance, created, **kwargs):
    """Handle new anomaly detection"""
    if created:
        # Log to console (could send to logging service)
        print(f"[SECURITY] New {instance.severity} anomaly: {instance.title}")
        
        # Could trigger additional actions here
        # - Send to external SIEM
        # - Update metrics
        # - Notify monitoring systems


@receiver(post_save, sender=ThreatResponse)
def on_threat_response(sender, instance, created, **kwargs):
    """Handle threat response execution"""
    if created:
        print(f"[SECURITY] Response executed: {instance.action_taken} for anomaly {instance.anomaly.title}")

