"""
Kafka producer for asynchronous event publishing.
"""

import json
import logging
from typing import Dict, Optional
from aiokafka import AIOKafkaProducer
from django.conf import settings

logger = logging.getLogger(__name__)


class KafkaProducerService:
    """
    Async Kafka producer for publishing events.

    Topics:
    - ingest.events: Raw request events from edge
    - enriched.events: Enriched events with geo, UA, etc.
    - detect.requests: Requests for detection
    - detect.responses: Detection results
    - detection.events: Final detection alerts
    - policy.updates: Policy changes for edge sync
    - audit.events: Audit log events
    """

    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self._started = False

    async def start(self):
        """Start Kafka producer"""
        if self._started:
            return

        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            compression_type='lz4',
            acks='all',  # Wait for all replicas
            max_request_size=10485760,  # 10MB
        )

        await self.producer.start()
        self._started = True
        logger.info("Kafka producer started")

    async def stop(self):
        """Stop Kafka producer"""
        if self.producer and self._started:
            await self.producer.stop()
            self._started = False
            logger.info("Kafka producer stopped")

    async def send(
        self,
        topic: str,
        value: Dict,
        key: Optional[str] = None,
        partition_key: Optional[str] = None
    ):
        """
        Send message to Kafka topic.

        Args:
            topic: Topic name (use settings.KAFKA_TOPICS)
            value: Message value (dict, will be JSON serialized)
            key: Optional message key
            partition_key: Optional partition key (default: key or org_id from value)

        Returns:
            RecordMetadata from Kafka
        """
        if not self._started:
            await self.start()

        # Use org_id as partition key for consistent hashing
        if partition_key is None:
            partition_key = key or value.get('org_id', 'default')

        try:
            metadata = await self.producer.send(
                topic,
                value=value,
                key=partition_key
            )
            logger.debug(f"Sent to {topic}: partition={metadata.partition}, offset={metadata.offset}")
            return metadata

        except Exception as e:
            logger.error(f"Failed to send to Kafka topic {topic}: {e}", exc_info=True)
            raise

    async def send_ingest_event(self, event: Dict):
        """Send raw ingest event"""
        await self.send(settings.KAFKA_TOPICS['INGEST_EVENTS'], event)

    async def send_enriched_event(self, event: Dict):
        """Send enriched event"""
        await self.send(settings.KAFKA_TOPICS['ENRICHED_EVENTS'], event)

    async def send_detection_event(self, detection: Dict):
        """Send detection alert"""
        await self.send(settings.KAFKA_TOPICS['DETECTION_EVENTS'], detection)

    async def send_policy_update(self, policy_update: Dict):
        """Send policy update"""
        await self.send(settings.KAFKA_TOPICS['POLICY_UPDATES'], policy_update)

    async def send_audit_event(self, audit: Dict):
        """Send audit event"""
        await self.send(settings.KAFKA_TOPICS['AUDIT_EVENTS'], audit)


# Singleton instance
kafka_producer = KafkaProducerService()
