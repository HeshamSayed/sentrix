"""
Dashboard aggregation views.
Provides summary data for dashboard UI.
"""
import logging
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.models import Organization, Application, User, APIEndpoint, UsageTracking
from detection.models import DetectionEvent

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    """
    Get comprehensive dashboard summary for user's organization.

    GET /v1/dashboard/summary/?app_id={app_id}&hours={hours}

    Query params:
        app_id (optional): Filter by specific application
        hours (optional): Time window in hours (default: 24)

    Returns:
    {
        "overview": {
            "total_applications": 5,
            "total_users": 12,
            "total_endpoints": 150
        },
        "traffic": {
            "requests_24h": 125000,
            "blocked_24h": 450,
            "block_rate": 0.36
        },
        "detections": {
            "total": 45,
            "open": 12,
            "critical": 3,
            "high": 8,
            "recent": [...]
        },
        "quota": {
            "applications": {...},
            "users": {...},
            "requests": {...}
        }
    }
    """
    user = request.user
    org_id = user.org_id

    # Get query parameters
    app_id = request.query_params.get('app_id')
    hours = int(request.query_params.get('hours', 24))
    time_threshold = timezone.now() - timedelta(hours=hours)

    # Build base querysets
    apps_qs = Application.objects.filter(org_id=org_id, is_active=True)
    users_qs = User.objects.filter(org_id=org_id, is_active=True)
    endpoints_qs = APIEndpoint.objects.filter(org_id=org_id)
    detections_qs = DetectionEvent.objects.filter(org_id=org_id)
    usage_qs = UsageTracking.objects.filter(org_id=org_id)

    # Apply app filter if specified
    if app_id:
        apps_qs = apps_qs.filter(app_id=app_id)
        endpoints_qs = endpoints_qs.filter(app_id=app_id)
        detections_qs = detections_qs.filter(app_id=app_id)
        usage_qs = usage_qs.filter(app_id=app_id)

    # Overview stats
    overview = {
        'total_applications': apps_qs.count(),
        'total_users': users_qs.count(),
        'total_endpoints': endpoints_qs.count(),
    }

    # Traffic stats (from usage tracking)
    traffic_period = timezone.now() - timedelta(hours=hours)
    recent_usage = usage_qs.filter(period_start__gte=traffic_period).aggregate(
        total_requests=Sum('request_count'),
        total_blocked=Sum('blocked_count'),
        total_r1_calls=Sum('r1_invocation_count')
    )

    total_requests = recent_usage['total_requests'] or 0
    total_blocked = recent_usage['total_blocked'] or 0

    traffic = {
        'requests_24h': total_requests,
        'blocked_24h': total_blocked,
        'block_rate': round((total_blocked / total_requests * 100), 2) if total_requests > 0 else 0,
        'r1_invocations_24h': recent_usage['total_r1_calls'] or 0
    }

    # Detection stats
    recent_detections = detections_qs.filter(detected_at__gte=time_threshold)
    detection_counts = recent_detections.values('status').annotate(count=Count('status'))
    status_dict = {item['status']: item['count'] for item in detection_counts}

    severity_counts = recent_detections.values('severity').annotate(count=Count('severity'))
    severity_dict = {item['severity']: item['count'] for item in severity_counts}

    # Recent detections (last 5)
    from detection.serializers import DetectionEventSerializer
    recent_detection_list = detections_qs.select_related(
        'org', 'app', 'endpoint', 'assigned_to'
    ).order_by('-detected_at')[:5]
    recent_detection_data = DetectionEventSerializer(recent_detection_list, many=True).data

    detections = {
        'total': recent_detections.count(),
        'open': status_dict.get('open', 0),
        'investigating': status_dict.get('investigating', 0),
        'critical': severity_dict.get('critical', 0),
        'high': severity_dict.get('high', 0),
        'medium': severity_dict.get('medium', 0),
        'by_severity': severity_dict,
        'by_status': status_dict,
        'recent': recent_detection_data
    }

    # Quota info (from subscription)
    org = Organization.objects.get(org_id=org_id)
    subscription = org.get_active_subscription()

    if subscription:
        # Application quota
        current_apps = apps_qs.count()
        apps_quota = {
            'current': current_apps,
            'limit': subscription.quota_max_applications,
            'available': subscription.quota_max_applications - current_apps,
            'usage_percent': round((current_apps / subscription.quota_max_applications * 100), 2)
        }

        # User quota
        current_users = users_qs.count()
        users_quota = {
            'current': current_users,
            'limit': subscription.quota_max_users,
            'available': subscription.quota_max_users - current_users,
            'usage_percent': round((current_users / subscription.quota_max_users * 100), 2)
        }

        # Request quota (current month)
        current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_usage = usage_qs.filter(period_start__gte=current_month_start).aggregate(
            total=Sum('request_count')
        )
        current_requests = month_usage['total'] or 0

        requests_quota = {
            'current': current_requests,
            'limit': subscription.quota_requests_per_month,
            'available': subscription.quota_requests_per_month - current_requests,
            'usage_percent': round((current_requests / subscription.quota_requests_per_month * 100), 2),
            'period_start': current_month_start.isoformat()
        }

        quota = {
            'applications': apps_quota,
            'users': users_quota,
            'requests': requests_quota
        }
    else:
        quota = None

    # Assemble response
    summary = {
        'overview': overview,
        'traffic': traffic,
        'detections': detections,
        'quota': quota,
        'period_hours': hours
    }

    return Response(summary)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def metrics_timeseries(request):
    """
    Get time-series metrics for charts.

    GET /v1/dashboard/metrics/?app_id={app_id}&metric={metric}&start={start}&end={end}&interval={interval}

    Query params:
        app_id (optional): Filter by application
        metric: Metric name (requests, blocked, detections, latency)
        start: Start time (ISO 8601)
        end: End time (ISO 8601)
        interval: Grouping interval (hour, day)

    Returns:
    {
        "metric": "requests",
        "interval": "hour",
        "data": [
            {"timestamp": "2025-11-14T00:00:00Z", "value": 1250},
            {"timestamp": "2025-11-14T01:00:00Z", "value": 1180},
            ...
        ]
    }
    """
    user = request.user
    org_id = user.org_id

    # Get query parameters
    app_id = request.query_params.get('app_id')
    metric = request.query_params.get('metric', 'requests')
    start_str = request.query_params.get('start')
    end_str = request.query_params.get('end')
    interval = request.query_params.get('interval', 'hour')

    # Parse dates
    if start_str:
        start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
    else:
        start = timezone.now() - timedelta(hours=24)

    if end_str:
        end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
    else:
        end = timezone.now()

    # TODO: Implement time-series aggregation
    # For now, return placeholder data
    data = []

    # This would typically aggregate from usage_tracking or api_request_event
    # and bucket by time interval

    response = {
        'metric': metric,
        'interval': interval,
        'start': start.isoformat(),
        'end': end.isoformat(),
        'data': data,
        'note': 'Time-series aggregation not yet implemented'
    }

    return Response(response)
