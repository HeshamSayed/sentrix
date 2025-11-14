"""
Deepseek-R1 model client for real-time threat detection.
"""

import logging
from typing import Dict, Optional
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class DeepseekR1Client:
    """
    Async client for Deepseek-R1 model server.

    Pools:
    - Real-time: low-latency inference (< 25ms target)
    - Batch: deeper analysis (< 500ms acceptable)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        realtime_timeout_ms: Optional[int] = None,
        batch_timeout_ms: Optional[int] = None
    ):
        self.base_url = base_url or settings.R1_MODEL_SERVER_URL
        self.realtime_timeout_ms = realtime_timeout_ms or settings.R1_REALTIME_TIMEOUT_MS
        self.batch_timeout_ms = batch_timeout_ms or settings.R1_BATCH_TIMEOUT_MS

        # Separate clients for different timeout requirements
        self.realtime_client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.realtime_timeout_ms / 1000.0  # Convert to seconds
        )
        self.batch_client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.batch_timeout_ms / 1000.0
        )

    async def close(self):
        """Close HTTP clients"""
        await self.realtime_client.aclose()
        await self.batch_client.aclose()

    async def infer_realtime(self, features: Dict) -> Dict:
        """
        Real-time inference (strict timeout).

        Args:
            features: Request features
            {
                "method": "POST",
                "path": "/payments/charge",
                "client_ip": "1.2.3.4",
                "anomalies": ["rate_spike"],
                ...
            }

        Returns:
            {
                "score": 0.0-1.0,
                "verdict": "benign" | "suspicious" | "malicious",
                "explanation": "...",
                "model_version": "r1-distill-v1",
                "latency_ms": 15.2
            }

        Raises:
            httpx.TimeoutException: If inference exceeds timeout
            httpx.HTTPError: If model server error
        """
        try:
            response = await self.realtime_client.post(
                "/v1/infer",
                json={"features": features, "max_tokens": 256}
            )
            response.raise_for_status()
            result = response.json()

            logger.info(
                f"R1 realtime inference: score={result.get('score')}, "
                f"latency={result.get('latency_ms')}ms"
            )
            return result

        except httpx.TimeoutException:
            logger.warning(f"R1 realtime inference timeout (>{self.realtime_timeout_ms}ms)")
            return {
                "score": None,
                "verdict": "unknown",
                "explanation": "Model inference timed out",
                "error": "timeout"
            }

        except httpx.HTTPError as e:
            logger.error(f"R1 realtime inference error: {e}")
            return {
                "score": None,
                "verdict": "unknown",
                "explanation": "Model server error",
                "error": str(e)
            }

    async def infer_batch(self, features: Dict) -> Dict:
        """
        Batch inference (relaxed timeout for deeper analysis).

        Args:
            features: Request features (same as realtime)

        Returns:
            Same format as infer_realtime
        """
        try:
            response = await self.batch_client.post(
                "/v1/infer",
                json={"features": features, "max_tokens": 512}  # More tokens for detailed analysis
            )
            response.raise_for_status()
            result = response.json()

            logger.info(
                f"R1 batch inference: score={result.get('score')}, "
                f"latency={result.get('latency_ms')}ms"
            )
            return result

        except httpx.TimeoutException:
            logger.warning(f"R1 batch inference timeout (>{self.batch_timeout_ms}ms)")
            return {
                "score": None,
                "verdict": "unknown",
                "explanation": "Model inference timed out",
                "error": "timeout"
            }

        except httpx.HTTPError as e:
            logger.error(f"R1 batch inference error: {e}")
            return {
                "score": None,
                "verdict": "unknown",
                "explanation": "Model server error",
                "error": str(e)
            }

    async def health_check(self) -> bool:
        """
        Check if model server is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self.realtime_client.get("/health", timeout=5.0)
            response.raise_for_status()
            data = response.json()
            is_healthy = data.get('status') == 'healthy'
            logger.debug(f"R1 model health check: {is_healthy}")
            return is_healthy

        except Exception as e:
            logger.error(f"R1 model health check failed: {e}")
            return False


# Singleton instance
r1_client = DeepseekR1Client()
