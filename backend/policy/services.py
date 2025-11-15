"""
Policy services for simulation, caching, and management.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from django.db.models import Q, Count
from django.utils import timezone
from django.core.cache import cache
from asgiref.sync import sync_to_async

from core.models import Organization, Application
from .models import Policy
from .evaluator import PolicyEvaluator


class PolicySimulationService:
    """
    Simulates policy impact on historical data.
    """

    def __init__(self):
        self.evaluator = PolicyEvaluator()

    async def simulate_policy(
        self,
        org_id: str,
        app_id: Optional[str],
        condition: Dict[str, Any],
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Simulate policy against historical events.

        Args:
            org_id: Organization ID
            app_id: Application ID (None for org-level)
            condition: Policy condition DSL
            days: Number of days to simulate (default: 7)

        Returns:
            Simulation results with affected request counts
        """
        from core.models import APIRequestEvent

        # Calculate date range
        end_time = timezone.now()
        start_time = end_time - timedelta(days=days)

        # Build base queryset (filtered by org and app)
        queryset = APIRequestEvent.objects.filter(
            org_id=org_id,
            timestamp__gte=start_time,
            timestamp__lte=end_time
        )

        if app_id:
            queryset = queryset.filter(app_id=app_id)

        # Get sample of events (limit to 10k for performance)
        # In production, this could be optimized with sampling or aggregation
        total_requests = await sync_to_async(queryset.count)()
        sample_events = await sync_to_async(list)(
            queryset.order_by('-timestamp')[:10000].values(
                'method', 'path', 'path_pattern', 'client_ip',
                'request_meta', 'response_meta', 'decision_action'
            )
        )

        # Evaluate condition against each event
        affected_count = 0
        would_block_count = 0
        sample_matches = []

        for event in sample_events:
            try:
                if self.evaluator.evaluate(condition, event):
                    affected_count += 1

                    # Assume action would be block (could be parameterized)
                    if event.get('decision_action') != 'block':
                        would_block_count += 1

                    # Store sample matches (first 10)
                    if len(sample_matches) < 10:
                        sample_matches.append({
                            'method': event.get('method'),
                            'path': event.get('path'),
                            'client_ip': event.get('client_ip'),
                            'current_action': event.get('decision_action'),
                        })
            except Exception:
                # Skip events that fail evaluation
                continue

        # Calculate impact
        impact_percentage = (affected_count / len(sample_events) * 100) if sample_events else 0

        # Extrapolate to full dataset if we sampled
        if total_requests > len(sample_events):
            extrapolation_factor = total_requests / len(sample_events)
            estimated_affected = int(affected_count * extrapolation_factor)
            estimated_would_block = int(would_block_count * extrapolation_factor)
        else:
            estimated_affected = affected_count
            estimated_would_block = would_block_count

        return {
            'date_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'days': days
            },
            'total_requests_analyzed': len(sample_events),
            'total_requests_in_period': total_requests,
            'sampled': total_requests > len(sample_events),
            'affected_requests': affected_count,
            'estimated_affected': estimated_affected,
            'would_block': would_block_count,
            'estimated_would_block': estimated_would_block,
            'impact_percentage': round(impact_percentage, 2),
            'sample_matches': sample_matches,
            'timestamp': timezone.now().isoformat()
        }


class PolicyCacheService:
    """
    Manages policy caching in Redis.
    """

    CACHE_TTL = 300  # 5 minutes
    CACHE_KEY_PREFIX = 'policies'

    @classmethod
    def _get_cache_key(cls, org_id: str, app_id: Optional[str] = None) -> str:
        """Get cache key for org/app policies."""
        if app_id:
            return f"{cls.CACHE_KEY_PREFIX}:org:{org_id}:app:{app_id}"
        return f"{cls.CACHE_KEY_PREFIX}:org:{org_id}"

    @classmethod
    async def get_policies(
        cls,
        org_id: str,
        app_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get policies from cache or database.

        Returns:
            List of policy dicts sorted by priority
        """
        # Try cache first
        cache_key = cls._get_cache_key(org_id, app_id)
        cached = cache.get(cache_key)

        if cached is not None:
            return cached

        # Fetch from database
        policies = await cls._fetch_policies_from_db(org_id, app_id)

        # Cache for future requests
        cache.set(cache_key, policies, cls.CACHE_TTL)

        return policies

    @classmethod
    async def _fetch_policies_from_db(
        cls,
        org_id: str,
        app_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch policies from database."""

        # Build queryset
        # Include both org-level policies and app-specific policies
        q_filter = Q(org_id=org_id, is_enabled=True)

        if app_id:
            # Include org-level policies (app=None) OR app-specific policies
            q_filter &= (Q(app_id=app_id) | Q(is_org_level=True, app=None))
        else:
            # Only org-level policies
            q_filter &= Q(is_org_level=True, app=None)

        # Fetch policies
        policies = await sync_to_async(list)(
            Policy.objects.filter(q_filter)
            .order_by('priority', '-created_at')
            .values(
                'policy_id', 'name', 'description',
                'condition', 'action', 'mode',
                'is_enabled', 'priority', 'is_org_level'
            )
        )

        # Convert UUIDs to strings for JSON serialization
        for policy in policies:
            policy['policy_id'] = str(policy['policy_id'])

        return policies

    @classmethod
    def invalidate_cache(cls, org_id: str, app_id: Optional[str] = None):
        """Invalidate policy cache."""
        if app_id:
            # Invalidate app-specific cache
            cache_key = cls._get_cache_key(org_id, app_id)
            cache.delete(cache_key)
        else:
            # Invalidate org-level cache and all app caches
            # Note: This requires fetching all apps (could be optimized)
            org_cache_key = cls._get_cache_key(org_id)
            cache.delete(org_cache_key)

            # Also invalidate app-specific caches
            # Use pattern matching if available (Redis)
            pattern = f"{cls.CACHE_KEY_PREFIX}:org:{org_id}:app:*"
            try:
                # This works with Redis backend
                from django.core.cache import caches
                redis_cache = caches['default']
                if hasattr(redis_cache, 'delete_pattern'):
                    redis_cache.delete_pattern(pattern)
            except Exception:
                # Fallback: just invalidate org-level
                pass


class PolicyPublisherService:
    """
    Publishes policy updates to Kafka for edge synchronization.
    """

    @staticmethod
    async def publish_policy_update(
        org_id: str,
        app_id: Optional[str] = None,
        event_type: str = 'policy.updated'
    ):
        """
        Publish policy update event to Kafka.

        Args:
            org_id: Organization ID
            app_id: Application ID (None for org-level)
            event_type: Event type (policy.created, policy.updated, policy.deleted, policy.enabled, policy.disabled)
        """
        from core.kafka.producer import get_kafka_producer

        # Build event
        event = {
            'event_type': event_type,
            'org_id': org_id,
            'app_id': app_id,
            'timestamp': timezone.now().isoformat()
        }

        # Publish to policy.updates topic
        producer = await get_kafka_producer()
        await producer.send(
            'policy.updates',
            value=json.dumps(event).encode('utf-8'),
            key=org_id.encode('utf-8')
        )


class PolicyManagementService:
    """
    High-level policy management operations.
    """

    def __init__(self):
        self.simulation_service = PolicySimulationService()
        self.cache_service = PolicyCacheService()
        self.publisher_service = PolicyPublisherService()

    async def create_policy(
        self,
        org_id: str,
        user_id: str,
        name: str,
        condition: Dict[str, Any],
        action: Dict[str, Any],
        app_id: Optional[str] = None,
        description: str = '',
        mode: str = 'observe',
        priority: int = 100
    ) -> Policy:
        """
        Create a new policy.

        Args:
            org_id: Organization ID
            user_id: Creator user ID
            name: Policy name
            condition: Policy condition DSL
            action: Policy action
            app_id: Application ID (None for org-level)
            description: Policy description
            mode: Policy mode (observe or enforce)
            priority: Priority (lower = higher priority)

        Returns:
            Created policy
        """
        # Create policy
        policy = await sync_to_async(Policy.objects.create)(
            org_id=org_id,
            app_id=app_id,
            name=name,
            description=description,
            condition=condition,
            action=action,
            mode=mode,
            priority=priority,
            is_org_level=(app_id is None),
            created_by_id=user_id,
            is_enabled=False  # Start disabled by default
        )

        # Invalidate cache
        self.cache_service.invalidate_cache(org_id, app_id)

        # Publish update
        await self.publisher_service.publish_policy_update(
            org_id, app_id, 'policy.created'
        )

        return policy

    async def enable_policy(self, policy_id: str):
        """Enable a policy."""
        policy = await sync_to_async(Policy.objects.get)(policy_id=policy_id)

        policy.is_enabled = True
        await sync_to_async(policy.save)(update_fields=['is_enabled', 'updated_at'])

        # Invalidate cache
        self.cache_service.invalidate_cache(str(policy.org_id), str(policy.app_id) if policy.app_id else None)

        # Publish update
        await self.publisher_service.publish_policy_update(
            str(policy.org_id),
            str(policy.app_id) if policy.app_id else None,
            'policy.enabled'
        )

    async def disable_policy(self, policy_id: str):
        """Disable a policy."""
        policy = await sync_to_async(Policy.objects.get)(policy_id=policy_id)

        policy.is_enabled = False
        await sync_to_async(policy.save)(update_fields=['is_enabled', 'updated_at'])

        # Invalidate cache
        self.cache_service.invalidate_cache(str(policy.org_id), str(policy.app_id) if policy.app_id else None)

        # Publish update
        await self.publisher_service.publish_policy_update(
            str(policy.org_id),
            str(policy.app_id) if policy.app_id else None,
            'policy.disabled'
        )

    async def simulate_policy(
        self,
        policy_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Simulate policy impact.

        Args:
            policy_id: Policy ID
            days: Number of days to simulate

        Returns:
            Simulation results
        """
        policy = await sync_to_async(Policy.objects.get)(policy_id=policy_id)

        # Run simulation
        results = await self.simulation_service.simulate_policy(
            org_id=str(policy.org_id),
            app_id=str(policy.app_id) if policy.app_id else None,
            condition=policy.condition,
            days=days
        )

        # Save simulation results
        policy.last_simulation_at = timezone.now()
        policy.last_simulation_result = results
        await sync_to_async(policy.save)(
            update_fields=['last_simulation_at', 'last_simulation_result', 'updated_at']
        )

        return results
