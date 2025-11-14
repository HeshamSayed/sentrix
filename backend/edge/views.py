"""
Edge API views - Decision API (ultra-fast path).
Target: < 25ms P95 latency.
"""

import logging
import time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from prometheus_client import Histogram, Counter

from .services.domain_resolver import domain_resolver
from .services.decision import decision_service

logger = logging.getLogger(__name__)

# Prometheus metrics
DECISION_LATENCY = Histogram(
    'decision_api_latency_seconds',
    'Decision API latency in seconds',
    buckets=[0.005, 0.010, 0.015, 0.020, 0.025, 0.030, 0.040, 0.050, 0.075, 0.100]
)
DECISION_COUNTER = Counter(
    'decision_api_total',
    'Total decision API calls',
    ['action']
)


class ProxyDecisionAPIView(APIView):
    """
    ULTRA-FAST decision API for edge proxies.

    Called by Nginx/OpenResty on every request.
    Must return within 25ms P95.

    POST /v1/edge/decision
    {
        "domain": "api.customer-payments.com",
        "method": "POST",
        "path": "/payments/charge/123",
        "client_ip": "1.2.3.4",
        "headers": {...},  // optional
        "body_hash": "sha256..."  // optional
    }

    Response:
    {
        "action": "allow",  // or "block", "throttle", "challenge"
        "reason": "no_threats_detected",
        "score": 0.1,
        "explanation": "...",
        "cache_ttl": 60
    }
    """

    permission_classes = []  # No auth required (called by edge, not user)
    authentication_classes = []

    async def post(self, request):
        start_time = time.time()

        try:
            # Parse request
            domain = request.data.get('domain')
            method = request.data.get('method')
            path = request.data.get('path')
            client_ip = request.data.get('client_ip')
            headers = request.data.get('headers', {})
            body_hash = request.data.get('body_hash')

            # Validate required fields
            if not all([domain, method, path, client_ip]):
                return Response(
                    {
                        "action": "allow",  # Fail open on invalid request
                        "reason": "invalid_request",
                        "score": 0.0,
                        "explanation": "Missing required fields",
                        "cache_ttl": 0
                    },
                    status=status.HTTP_200_OK
                )

            # Resolve domain → (org_id, app_id)
            app_context = await domain_resolver.resolve(domain)

            if not app_context:
                # Domain not found or not verified → fail open
                logger.warning(f"Domain not found: {domain}")
                return Response(
                    {
                        "action": "allow",
                        "reason": "domain_not_found",
                        "score": 0.0,
                        "explanation": "Domain not registered or verified",
                        "cache_ttl": 10
                    },
                    status=status.HTTP_200_OK
                )

            org_id = app_context['org_id']
            app_id = app_context['app_id']

            # Make decision
            decision = await decision_service.make_decision(
                org_id=org_id,
                app_id=app_id,
                method=method,
                path=path,
                client_ip=client_ip,
                headers=headers,
                body_hash=body_hash
            )

            # Record metrics
            latency = time.time() - start_time
            DECISION_LATENCY.observe(latency)
            DECISION_COUNTER.labels(action=decision['action']).inc()

            if latency > 0.025:  # > 25ms
                logger.warning(
                    f"Slow decision: {latency*1000:.2f}ms (org={org_id}, app={app_id}, path={path})"
                )

            return Response(decision, status=status.HTTP_200_OK)

        except Exception as e:
            # Fail open on error
            logger.error(f"Decision API error: {e}", exc_info=True)
            latency = time.time() - start_time
            DECISION_LATENCY.observe(latency)

            return Response(
                {
                    "action": "allow",  # Fail open
                    "reason": "internal_error",
                    "score": 0.0,
                    "explanation": "Internal error, failing open",
                    "cache_ttl": 0
                },
                status=status.HTTP_200_OK
            )
