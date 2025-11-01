"""
Celery Beat schedule for automated tasks
"""

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Auto-verify DNS records every 5 minutes
    'auto-verify-dns-records': {
        'task': 'applications.tasks.auto_verify_dns_records',
        'schedule': 300.0,  # Every 5 minutes
        'options': {'expires': 240}
    },
    
    # Check application health every 2 minutes
    'check-application-health': {
        'task': 'applications.tasks.check_application_health',
        'schedule': 120.0,  # Every 2 minutes
        'options': {'expires': 100}
    },
    
    # Cleanup expired verification tokens daily
    'cleanup-expired-tokens': {
        'task': 'applications.tasks.cleanup_expired_verification_tokens',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}

