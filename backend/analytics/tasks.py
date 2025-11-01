from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from applications.models import Application
from organizations.models import Organization
from analytics.models import Alert

@shared_task
def check_quota_usage():
    """Check quota usage and create alerts if needed"""
    organizations = Organization.objects.filter(is_active=True)
    
    for org in organizations:
        # Check organization quota
        if org.quota_percentage >= 90:
            Alert.objects.get_or_create(
                organization=org,
                alert_type='QUOTA_WARNING' if org.quota_percentage < 100 else 'QUOTA_EXCEEDED',
                severity='WARNING' if org.quota_percentage < 100 else 'CRITICAL',
                is_resolved=False,
                defaults={
                    'title': f"Quota {'Warning' if org.quota_percentage < 100 else 'Exceeded'}",
                    'message': f"Organization quota is at {org.quota_percentage:.1f}%",
                    'data': {'quota_percentage': org.quota_percentage}
                }
            )
        
        # Check application quotas
        for app in org.applications.all():
            if app.quota_percentage >= 90:
                Alert.objects.get_or_create(
                    organization=org,
                    application=app,
                    alert_type='QUOTA_WARNING' if app.quota_percentage < 100 else 'QUOTA_EXCEEDED',
                    severity='WARNING' if app.quota_percentage < 100 else 'ERROR',
                    is_resolved=False,
                    defaults={
                        'title': f"Application Quota {'Warning' if app.quota_percentage < 100 else 'Exceeded'}",
                        'message': f"Application '{app.name}' quota is at {app.quota_percentage:.1f}%",
                        'data': {'quota_percentage': app.quota_percentage}
                    }
                )

@shared_task
def aggregate_metrics():
    """Aggregate metrics from raw data"""
    # This would aggregate Kafka stream data into MetricSnapshot records
    # Implementation would depend on your data pipeline
    pass

@shared_task
def detect_anomalies():
    """Detect anomalies in traffic patterns"""
    # This would use ML or statistical methods to detect anomalies
    # Implementation would depend on your detection algorithms
    pass

