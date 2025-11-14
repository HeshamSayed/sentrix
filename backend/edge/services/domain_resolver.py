"""
Domain resolution service.
Resolves customer domains to (org_id, app_id) context.
"""

import json
import logging
from typing import Optional, Tuple
from uuid import UUID

import redis.asyncio as aioredis
from django.conf import settings
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class DomainResolver:
    """
    Resolves domain → (org_id, app_id) with Redis caching.

    Redis cache key: domain:{domain}
    Value: {"org_id": "...", "app_id": "...", "origin_url": "...", "failover_mode": "..."}
    TTL: 60 seconds
    """

    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self.cache_ttl = 60  # 1 minute

    async def connect_redis(self):
        """Initialize Redis connection"""
        if not self.redis_client:
            self.redis_client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )

    async def close_redis(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    async def resolve(self, domain: str) -> Optional[dict]:
        """
        Resolve domain to app context.

        Args:
            domain: Customer domain (e.g., "api.customer-payments.com")

        Returns:
            Dict with org_id, app_id, origin_url, failover_mode or None if not found
        """
        await self.connect_redis()

        # Try cache first
        cache_key = f"domain:{domain}"
        cached = await self.redis_client.get(cache_key)

        if cached:
            logger.debug(f"Domain resolution cache HIT: {domain}")
            return json.loads(cached)

        logger.debug(f"Domain resolution cache MISS: {domain}")

        # Fetch from database
        context = await self._fetch_from_db(domain)

        if context:
            # Cache for 60 seconds
            await self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(context)
            )

        return context

    @sync_to_async
    def _fetch_from_db(self, domain: str) -> Optional[dict]:
        """Fetch domain context from DB (sync function wrapped in async)"""
        from core.models import Application

        try:
            app = Application.objects.select_related('org').get(
                domain=domain,
                is_active=True,
                dns_verified=True
            )

            context = {
                'org_id': str(app.org_id),
                'app_id': str(app.app_id),
                'origin_url': app.origin_url,
                'failover_mode': app.failover_mode,
                'org_name': app.org.name,
                'app_name': app.name,
            }

            logger.info(f"Resolved domain: {domain} → org={app.org_id}, app={app.app_id}")
            return context

        except Application.DoesNotExist:
            logger.warning(f"Domain not found or not verified: {domain}")
            return None

    async def invalidate(self, domain: str):
        """
        Invalidate cached domain resolution.
        Call this when application domain or status changes.
        """
        await self.connect_redis()
        cache_key = f"domain:{domain}"
        deleted = await self.redis_client.delete(cache_key)
        logger.info(f"Invalidated domain cache: {domain} (deleted={deleted})")


# Singleton instance
domain_resolver = DomainResolver()
