import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('sentrix')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    'check-quota-usage': {
        'task': 'analytics.tasks.check_quota_usage',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'aggregate-metrics': {
        'task': 'analytics.tasks.aggregate_metrics',
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
    },
    'detect-anomalies': {
        'task': 'analytics.tasks.detect_anomalies',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    # Security tasks
    'update-behavior-baselines': {
        'task': 'security.tasks.update_all_baselines',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'cleanup-old-behavior-logs': {
        'task': 'security.tasks.cleanup_old_behavior_logs',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'unblock-expired-entities': {
        'task': 'security.tasks.unblock_expired_entities',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'generate-security-report': {
        'task': 'security.tasks.generate_security_report',
        'schedule': crontab(hour=8, minute=0),  # Daily at 8 AM
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

