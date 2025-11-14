"""
Configuration inheritance service.
Manages org-level defaults and app-level overrides with Redis caching.
"""

import json
import logging
from typing import Dict, Optional
from uuid import UUID

import redis.asyncio as aioredis
from django.conf import settings
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class ConfigService:
    """
    Manages configuration inheritance and caching.

    Hierarchy:
    - Organization has default_config (JSONB)
    - Application has custom_config (JSONB)
    - Merged = org.default_config + app.custom_config

    Redis cache key: config:org:{org_id}:app:{app_id}
    TTL: 5 minutes (300 seconds)
    """

    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self.cache_ttl = 300  # 5 minutes

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

    async def get_merged_config(self, org_id: UUID, app_id: UUID) -> Dict:
        """
        Get merged configuration for an application.
        Returns org defaults merged with app overrides.

        Args:
            org_id: Organization UUID
            app_id: Application UUID

        Returns:
            Merged configuration dict

        Raises:
            ValueError: If org or app not found
        """
        await self.connect_redis()

        # Try cache first
        cache_key = f"config:org:{org_id}:app:{app_id}"
        cached = await self.redis_client.get(cache_key)

        if cached:
            logger.debug(f"Config cache HIT: {cache_key}")
            return json.loads(cached)

        logger.debug(f"Config cache MISS: {cache_key}")

        # Fetch from database
        merged = await self._fetch_and_merge(org_id, app_id)

        # Cache for 5 minutes
        await self.redis_client.setex(
            cache_key,
            self.cache_ttl,
            json.dumps(merged)
        )

        return merged

    @sync_to_async
    def _fetch_and_merge(self, org_id: UUID, app_id: UUID) -> Dict:
        """Fetch from DB and merge (sync function wrapped in async)"""
        from core.models import Organization, Application

        try:
            org = Organization.objects.get(org_id=org_id)
        except Organization.DoesNotExist:
            raise ValueError(f"Organization {org_id} not found")

        try:
            app = Application.objects.select_related('org').get(
                app_id=app_id,
                org_id=org_id
            )
        except Application.DoesNotExist:
            raise ValueError(f"Application {app_id} not found in org {org_id}")

        # Merge: org defaults + app overrides
        merged = {**org.default_config, **app.custom_config}

        logger.info(f"Merged config for org={org_id}, app={app_id}")
        return merged

    async def invalidate_app_config(self, org_id: UUID, app_id: UUID):
        """
        Invalidate cached config for a specific app.
        Call this when app.custom_config is updated.
        """
        await self.connect_redis()
        cache_key = f"config:org:{org_id}:app:{app_id}"
        deleted = await self.redis_client.delete(cache_key)
        logger.info(f"Invalidated config cache: {cache_key} (deleted={deleted})")

    async def invalidate_org_configs(self, org_id: UUID):
        """
        Invalidate cached configs for ALL apps in an organization.
        Call this when org.default_config is updated.
        """
        await self.connect_redis()

        # Get all app IDs for this org
        from core.models import Application
        app_ids = await sync_to_async(list)(
            Application.objects.filter(org_id=org_id).values_list('app_id', flat=True)
        )

        # Delete all cached configs
        if app_ids:
            cache_keys = [f"config:org:{org_id}:app:{app_id}" for app_id in app_ids]
            deleted = await self.redis_client.delete(*cache_keys)
            logger.info(f"Invalidated {deleted} config caches for org={org_id}")

    async def get_config_value(
        self,
        org_id: UUID,
        app_id: UUID,
        key: str,
        default=None
    ):
        """
        Get a specific config value for an app.

        Args:
            org_id: Organization UUID
            app_id: Application UUID
            key: Config key (e.g., "rate_limit_rpm")
            default: Default value if key not found

        Returns:
            Config value or default
        """
        config = await self.get_merged_config(org_id, app_id)
        return config.get(key, default)


# Singleton instance
config_service = ConfigService()
