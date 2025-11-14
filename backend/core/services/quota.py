"""
Subscription and quota enforcement service.
Validates quotas before creating resources or processing requests.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from uuid import UUID

from asgiref.sync import sync_to_async
from django.utils import timezone
from django.db.models import Sum

logger = logging.getLogger(__name__)


class QuotaExceeded(Exception):
    """Raised when quota is exceeded"""
    def __init__(self, message: str, quota_type: str, current: int, limit: int):
        self.message = message
        self.quota_type = quota_type
        self.current = current
        self.limit = limit
        super().__init__(self.message)


class QuotaService:
    """
    Manages subscription quotas and enforcement.

    Quota types:
    - Applications: max number of active applications per org
    - Users: max number of active user seats per org
    - Requests: max API requests per month per org
    """

    @sync_to_async
    def check_application_quota(self, org_id: UUID) -> Tuple[bool, Dict]:
        """
        Check if org can create another application.

        Args:
            org_id: Organization UUID

        Returns:
            Tuple of (can_create: bool, quota_info: dict)

        Raises:
            ValueError: If org or subscription not found
        """
        from core.models import Organization

        try:
            org = Organization.objects.get(org_id=org_id)
        except Organization.DoesNotExist:
            raise ValueError(f"Organization {org_id} not found")

        subscription = org.get_active_subscription()
        if not subscription:
            raise ValueError(f"No active subscription for org {org_id}")

        current_count = org.applications.filter(is_active=True).count()
        can_create = current_count < subscription.quota_max_applications

        quota_info = {
            'quota_type': 'applications',
            'current': current_count,
            'limit': subscription.quota_max_applications,
            'available': subscription.quota_max_applications - current_count,
            'can_create': can_create
        }

        logger.info(f"Application quota check: org={org_id}, {quota_info}")
        return can_create, quota_info

    async def enforce_application_quota(self, org_id: UUID):
        """
        Enforce application quota (raise exception if exceeded).

        Args:
            org_id: Organization UUID

        Raises:
            QuotaExceeded: If quota exceeded
            ValueError: If org or subscription not found
        """
        can_create, quota_info = await self.check_application_quota(org_id)

        if not can_create:
            raise QuotaExceeded(
                message=f"Application quota exceeded. Current: {quota_info['current']}, Limit: {quota_info['limit']}",
                quota_type='applications',
                current=quota_info['current'],
                limit=quota_info['limit']
            )

    @sync_to_async
    def check_user_quota(self, org_id: UUID) -> Tuple[bool, Dict]:
        """
        Check if org can create another user.

        Args:
            org_id: Organization UUID

        Returns:
            Tuple of (can_create: bool, quota_info: dict)

        Raises:
            ValueError: If org or subscription not found
        """
        from core.models import Organization

        try:
            org = Organization.objects.get(org_id=org_id)
        except Organization.DoesNotExist:
            raise ValueError(f"Organization {org_id} not found")

        subscription = org.get_active_subscription()
        if not subscription:
            raise ValueError(f"No active subscription for org {org_id}")

        current_count = org.users.filter(is_active=True).count()
        can_create = current_count < subscription.quota_max_users

        quota_info = {
            'quota_type': 'users',
            'current': current_count,
            'limit': subscription.quota_max_users,
            'available': subscription.quota_max_users - current_count,
            'can_create': can_create
        }

        logger.info(f"User quota check: org={org_id}, {quota_info}")
        return can_create, quota_info

    async def enforce_user_quota(self, org_id: UUID):
        """
        Enforce user quota (raise exception if exceeded).

        Args:
            org_id: Organization UUID

        Raises:
            QuotaExceeded: If quota exceeded
            ValueError: If org or subscription not found
        """
        can_create, quota_info = await self.check_user_quota(org_id)

        if not can_create:
            raise QuotaExceeded(
                message=f"User license quota exceeded. Current: {quota_info['current']}, Limit: {quota_info['limit']}",
                quota_type='users',
                current=quota_info['current'],
                limit=quota_info['limit']
            )

    @sync_to_async
    def check_request_quota(self, org_id: UUID) -> Tuple[bool, Dict]:
        """
        Check if org can process more requests this month.

        Args:
            org_id: Organization UUID

        Returns:
            Tuple of (can_process: bool, quota_info: dict)

        Raises:
            ValueError: If org or subscription not found
        """
        from core.models import Organization, UsageTracking

        try:
            org = Organization.objects.get(org_id=org_id)
        except Organization.DoesNotExist:
            raise ValueError(f"Organization {org_id} not found")

        subscription = org.get_active_subscription()
        if not subscription:
            raise ValueError(f"No active subscription for org {org_id}")

        # Get current month usage
        current_month_start = timezone.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        usage_sum = UsageTracking.objects.filter(
            org_id=org_id,
            period_start__gte=current_month_start
        ).aggregate(
            total=Sum('request_count')
        )

        current_usage = usage_sum['total'] or 0
        can_process = current_usage < subscription.quota_requests_per_month

        quota_info = {
            'quota_type': 'requests_per_month',
            'current': current_usage,
            'limit': subscription.quota_requests_per_month,
            'available': subscription.quota_requests_per_month - current_usage,
            'can_process': can_process,
            'period_start': current_month_start.isoformat(),
        }

        return can_process, quota_info

    async def enforce_request_quota(self, org_id: UUID):
        """
        Enforce request quota (raise exception if exceeded).

        Args:
            org_id: Organization UUID

        Raises:
            QuotaExceeded: If quota exceeded
            ValueError: If org or subscription not found
        """
        can_process, quota_info = await self.check_request_quota(org_id)

        if not can_process:
            raise QuotaExceeded(
                message=f"Monthly request quota exceeded. Current: {quota_info['current']}, Limit: {quota_info['limit']}",
                quota_type='requests_per_month',
                current=quota_info['current'],
                limit=quota_info['limit']
            )

    @sync_to_async
    def check_feature_enabled(self, org_id: UUID, feature_name: str) -> bool:
        """
        Check if a feature is enabled for the organization's subscription.

        Args:
            org_id: Organization UUID
            feature_name: Feature name (e.g., "r1_realtime", "threat_hunting")

        Returns:
            True if feature is enabled, False otherwise

        Raises:
            ValueError: If org or subscription not found
        """
        from core.models import Organization

        try:
            org = Organization.objects.get(org_id=org_id)
        except Organization.DoesNotExist:
            raise ValueError(f"Organization {org_id} not found")

        subscription = org.get_active_subscription()
        if not subscription:
            raise ValueError(f"No active subscription for org {org_id}")

        is_enabled = subscription.is_feature_enabled(feature_name)
        logger.debug(f"Feature check: org={org_id}, feature={feature_name}, enabled={is_enabled}")
        return is_enabled

    async def get_quota_summary(self, org_id: UUID) -> Dict:
        """
        Get complete quota summary for an organization.

        Args:
            org_id: Organization UUID

        Returns:
            Dict with all quota information
        """
        # Run all checks in parallel
        app_can, app_info = await self.check_application_quota(org_id)
        user_can, user_info = await self.check_user_quota(org_id)
        req_can, req_info = await self.check_request_quota(org_id)

        return {
            'applications': app_info,
            'users': user_info,
            'requests': req_info,
        }


# Singleton instance
quota_service = QuotaService()
