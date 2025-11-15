"""
Decision service - fast path for allow/block decisions.
Target: < 25ms P95 latency.
"""

import hashlib
import json
import logging
from typing import Dict, Optional
from uuid import UUID

import redis.asyncio as aioredis
from django.conf import settings

# Import policy engine
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from policy.evaluator import PolicyMatcher
from policy.services import PolicyCacheService

logger = logging.getLogger(__name__)


class DecisionService:
    """
    Ultra-fast decision service with Redis caching.

    Decision flow:
    1. Compute fingerprint (org + app + path + method + client_ip)
    2. Check Redis cache
    3. If miss, run deterministic checks
    4. Call R1 model if needed (with strict timeout)
    5. Cache decision with TTL
    """

    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self.policy_matcher = PolicyMatcher()
        self.policy_cache = PolicyCacheService()

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

    def compute_fingerprint(
        self,
        org_id: str,
        app_id: str,
        method: str,
        path: str,
        client_ip: str
    ) -> str:
        """
        Compute request fingerprint for caching.

        Args:
            org_id: Organization ID
            app_id: Application ID
            method: HTTP method
            path: Request path
            client_ip: Client IP address

        Returns:
            SHA256 hex digest
        """
        data = f"{org_id}:{app_id}:{method}:{path}:{client_ip}"
        return hashlib.sha256(data.encode()).hexdigest()

    async def make_decision(
        self,
        org_id: str,
        app_id: str,
        method: str,
        path: str,
        client_ip: str,
        headers: Optional[Dict] = None,
        body_hash: Optional[str] = None,
    ) -> Dict:
        """
        Make allow/block decision for a request.

        Args:
            org_id: Organization ID
            app_id: Application ID
            method: HTTP method
            path: Request path
            client_ip: Client IP
            headers: Request headers (optional)
            body_hash: Request body hash (optional)

        Returns:
            Decision dict:
            {
                "action": "allow" | "block" | "throttle" | "challenge",
                "reason": "...",
                "score": 0.0-1.0,
                "explanation": "...",
                "cache_ttl": 60
            }
        """
        await self.connect_redis()

        # Compute fingerprint
        fingerprint = self.compute_fingerprint(org_id, app_id, method, path, client_ip)
        cache_key = f"decision:{fingerprint}"

        # Check cache
        cached = await self.redis_client.get(cache_key)
        if cached:
            logger.debug(f"Decision cache HIT: {fingerprint[:16]}...")
            return json.loads(cached)

        logger.debug(f"Decision cache MISS: {fingerprint[:16]}...")

        # Run decision logic
        decision = await self._evaluate_request(
            org_id, app_id, method, path, client_ip, headers, body_hash
        )

        # Cache decision
        cache_ttl = decision.get('cache_ttl', 60)
        await self.redis_client.setex(
            cache_key,
            cache_ttl,
            json.dumps(decision)
        )

        return decision

    async def _evaluate_request(
        self,
        org_id: str,
        app_id: str,
        method: str,
        path: str,
        client_ip: str,
        headers: Optional[Dict],
        body_hash: Optional[str],
    ) -> Dict:
        """
        Evaluate request and return decision.

        Decision precedence:
        1. Quota exceeded → block
        2. IP blacklist → block
        3. Rate limit → throttle
        4. Policy evaluation → action
        5. R1 model (if ambiguous) → decision
        6. Default → allow
        """
        # 1. Check quota (fast, from Redis)
        quota_ok = await self._check_quota(org_id)
        if not quota_ok:
            return {
                "action": "block",
                "reason": "quota_exceeded",
                "score": 1.0,
                "explanation": "Monthly request quota exceeded",
                "cache_ttl": 300  # Cache block for 5 minutes
            }

        # 2. Check IP blacklist (fast, from Redis)
        is_blacklisted = await self._check_ip_blacklist(client_ip)
        if is_blacklisted:
            return {
                "action": "block",
                "reason": "ip_blacklisted",
                "score": 1.0,
                "explanation": "Client IP is blacklisted",
                "cache_ttl": 300
            }

        # 3. Check rate limit (Redis token bucket)
        rate_limit_ok = await self._check_rate_limit(org_id, app_id, client_ip)
        if not rate_limit_ok:
            return {
                "action": "throttle",
                "reason": "rate_limit_exceeded",
                "score": 0.8,
                "explanation": "Rate limit exceeded",
                "cache_ttl": 10  # Short TTL for throttle
            }

        # 4. Evaluate policies (loaded from Redis)
        policy_decision = await self._evaluate_policies(org_id, app_id, method, path, client_ip)
        if policy_decision:
            return policy_decision

        # 5. Default: allow
        return {
            "action": "allow",
            "reason": "no_threats_detected",
            "score": 0.1,
            "explanation": "Request passed all checks",
            "cache_ttl": 60
        }

    async def _check_quota(self, org_id: str) -> bool:
        """
        Check if org has quota remaining (fast check from Redis).

        For production: increment a Redis counter per request and compare against quota.
        Here we return True as a placeholder (real implementation in quota service).
        """
        # TODO: Implement fast quota check from Redis
        # For now, allow all requests (quota enforcement happens in quota service)
        return True

    async def _check_ip_blacklist(self, client_ip: str) -> bool:
        """
        Check if IP is blacklisted.
        Blacklist stored in Redis set: blacklist:ips
        """
        is_blacklisted = await self.redis_client.sismember("blacklist:ips", client_ip)
        return bool(is_blacklisted)

    async def _check_rate_limit(self, org_id: str, app_id: str, client_ip: str) -> bool:
        """
        Check rate limit using Redis token bucket.
        Key: ratelimit:{org_id}:{app_id}:{client_ip}

        For production: use sliding window or token bucket algorithm.
        Placeholder: allow 100 requests per minute per IP.
        """
        rate_limit_key = f"ratelimit:{org_id}:{app_id}:{client_ip}"

        # Increment counter
        current = await self.redis_client.incr(rate_limit_key)

        # Set TTL on first request
        if current == 1:
            await self.redis_client.expire(rate_limit_key, 60)  # 1 minute window

        # Check limit (default: 100 requests per minute)
        limit = 100
        return current <= limit

    async def _evaluate_policies(
        self,
        org_id: str,
        app_id: str,
        method: str,
        path: str,
        client_ip: str
    ) -> Optional[Dict]:
        """
        Evaluate enabled policies against request.

        Policies loaded from cache using PolicyCacheService.
        Returns policy action if match, else None.
        """
        # Load policies from cache (org-level + app-specific)
        try:
            policies = await self.policy_cache.get_policies(org_id, app_id)
        except Exception as e:
            logger.error(f"Failed to load policies: {e}")
            return None

        if not policies:
            # No policies configured
            return None

        # Build event for policy evaluation
        event = {
            'method': method,
            'path': path,
            'path_pattern': path,  # Could be enriched with pattern matching
            'client_ip': client_ip,
            'org_id': org_id,
            'app_id': app_id
        }

        # Filter only enforce-mode policies
        enforce_policies = [
            p for p in policies
            if p.get('is_enabled') and p.get('mode') == 'enforce'
        ]

        if not enforce_policies:
            return None

        # Use PolicyMatcher to find matching policy
        action = self.policy_matcher.match_policies(event, enforce_policies)

        if action:
            # Convert policy action to decision format
            action_type = action.get('type', 'block')
            policy_name = action.get('policy_name', 'unknown')

            return {
                "action": action_type,
                "reason": f"policy_matched:{policy_name}",
                "score": 1.0,
                "explanation": action.get('message', f"Matched policy: {policy_name}"),
                "policy_id": action.get('policy_id'),
                "policy_name": policy_name,
                "cache_ttl": 60
            }

        return None


# Singleton instance
decision_service = DecisionService()
