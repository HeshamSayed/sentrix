"""
Celery tasks for asynchronous behavioral analysis
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import APIBehaviorLog, AnomalyDetection, ThreatResponse, BlockedEntity
from .detector import BehavioralDetector
from .response import ThreatResponseHandler


@shared_task
def analyze_request_behavior(behavior_log_id):
    """Analyze a single request for behavioral anomalies"""
    try:
        behavior_log = APIBehaviorLog.objects.get(id=behavior_log_id)
    except APIBehaviorLog.DoesNotExist:
        return
    
    detector = BehavioralDetector()
    anomalies = detector.analyze_request(behavior_log)
    
    # Create anomaly records and trigger responses
    response_handler = ThreatResponseHandler()
    
    for anomaly_data in anomalies:
        anomaly = detector.create_anomaly_record(behavior_log, anomaly_data)
        response_handler.handle_anomaly(anomaly)


@shared_task
def update_all_baselines():
    """Periodic task to update all user behavior baselines"""
    from .models import UserBehaviorBaseline
    
    detector = BehavioralDetector()
    
    # Update baselines that haven't been updated recently
    stale_threshold = timezone.now() - timedelta(minutes=detector.config.model_update_frequency_minutes)
    
    stale_baselines = UserBehaviorBaseline.objects.filter(
        last_calculated__lt=stale_threshold
    )[:100]  # Process in batches
    
    for baseline in stale_baselines:
        # Get a recent log for this user/endpoint
        recent_log = APIBehaviorLog.objects.filter(
            user=baseline.user,
            endpoint=baseline.endpoint
        ).first()
        
        if recent_log:
            detector.update_baseline(baseline, recent_log)


@shared_task
def cleanup_old_behavior_logs():
    """Remove old behavior logs to manage storage"""
    retention_days = 90
    cutoff_date = timezone.now() - timedelta(days=retention_days)
    
    deleted_count, _ = APIBehaviorLog.objects.filter(
        timestamp__lt=cutoff_date
    ).delete()
    
    return f"Deleted {deleted_count} old behavior logs"


@shared_task
def unblock_expired_entities():
    """Unblock entities whose block period has expired"""
    now = timezone.now()
    
    expired_blocks = BlockedEntity.objects.filter(
        is_permanent=False,
        blocked_until__lt=now,
        unblocked_at__isnull=True
    )
    
    count = expired_blocks.update(
        unblocked_at=now
    )
    
    return f"Unblocked {count} entities"


@shared_task
def generate_security_report():
    """Generate daily security summary report"""
    from django.core.mail import send_mail
    from django.conf import settings
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    # Gather statistics
    stats = {
        'total_requests': APIBehaviorLog.objects.filter(
            timestamp__date=yesterday
        ).count(),
        'anomalies_detected': AnomalyDetection.objects.filter(
            timestamp__date=yesterday
        ).count(),
        'critical_threats': AnomalyDetection.objects.filter(
            timestamp__date=yesterday,
            severity='CRITICAL'
        ).count(),
        'blocked_entities': BlockedEntity.objects.filter(
            blocked_at__date=yesterday
        ).count(),
    }
    
    # Create report
    report = f"""
    Sentrix Security Daily Report - {yesterday}
    
    Summary:
    - Total API Requests: {stats['total_requests']:,}
    - Anomalies Detected: {stats['anomalies_detected']}
    - Critical Threats: {stats['critical_threats']}
    - Entities Blocked: {stats['blocked_entities']}
    
    Top Threats:
    """
    
    top_threats = AnomalyDetection.objects.filter(
        timestamp__date=yesterday,
        severity__in=['HIGH', 'CRITICAL']
    ).order_by('-risk_score')[:5]
    
    for i, threat in enumerate(top_threats, 1):
        report += f"\n{i}. [{threat.severity}] {threat.title} (Risk: {threat.risk_score:.1f})"
    
    # Send email (if configured)
    try:
        if hasattr(settings, 'SECURITY_ALERT_EMAIL'):
            send_mail(
                f'Sentrix Security Report - {yesterday}',
                report,
                settings.DEFAULT_FROM_EMAIL,
                [settings.SECURITY_ALERT_EMAIL],
                fail_silently=True,
            )
    except Exception as e:
        print(f"Failed to send security report: {e}")
    
    return report

