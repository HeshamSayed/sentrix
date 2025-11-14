"""
Enrichment consumer.
Consumes ingest.events, enriches with geo/UA/path_pattern, produces enriched.events.
"""

import asyncio
import json
import logging
from typing import Dict
from aiokafka import AIOKafkaConsumer
from django.conf import settings

from core.kafka.producer import kafka_producer

logger = logging.getLogger(__name__)


class EnrichmentConsumer:
    """
    Enrichment consumer:
    - Reads from: ingest.events
    - Writes to: enriched.events

    Enrichment steps:
    1. GeoIP lookup (country, city)
    2. User-Agent parsing
    3. Path canonicalization → path_pattern
    4. Endpoint discovery → endpoint_id
    """

    def __init__(self):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.running = False

    async def start(self):
        """Start consumer"""
        self.consumer = AIOKafkaConsumer(
            settings.KAFKA_TOPICS['INGEST_EVENTS'],
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id='enrichment-group',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=False,  # Manual commit after processing
            max_poll_records=500,  # Batch size
        )

        await self.consumer.start()
        await kafka_producer.start()
        self.running = True
        logger.info("Enrichment consumer started")

    async def stop(self):
        """Stop consumer"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
        logger.info("Enrichment consumer stopped")

    async def consume(self):
        """Main consumer loop"""
        await self.start()

        try:
            while self.running:
                # Poll messages
                result = await self.consumer.getmany(timeout_ms=1000, max_records=500)

                for tp, messages in result.items():
                    logger.info(f"Processing {len(messages)} messages from {tp.topic}")

                    for message in messages:
                        try:
                            event = message.value
                            enriched = await self.enrich_event(event)
                            await kafka_producer.send_enriched_event(enriched)

                        except Exception as e:
                            logger.error(f"Error enriching event: {e}", exc_info=True)

                    # Commit offset after batch
                    await self.consumer.commit()

        except Exception as e:
            logger.error(f"Enrichment consumer error: {e}", exc_info=True)
        finally:
            await self.stop()

    async def enrich_event(self, event: Dict) -> Dict:
        """
        Enrich a single event.

        Input:
        {
            "org_id": "...",
            "app_id": "...",
            "trace_id": "...",
            "timestamp": "...",
            "method": "POST",
            "path": "/payments/charge/123",
            "client_ip": "1.2.3.4",
            "user_agent": "...",
            "headers": {...},
            "body_hash": "...",
            "response_status": 200
        }

        Output (adds):
        {
            ...all above fields,
            "geo_country": "US",
            "geo_city": "San Francisco",
            "user_agent_parsed": {...},
            "path_pattern": "/payments/charge/{id}",
            "endpoint_id": "..."
        }
        """
        enriched = event.copy()

        # 1. GeoIP lookup
        geo_data = await self.geoip_lookup(event['client_ip'])
        enriched['geo_country'] = geo_data.get('country')
        enriched['geo_city'] = geo_data.get('city')

        # 2. User-Agent parsing
        ua_parsed = await self.parse_user_agent(event.get('user_agent', ''))
        enriched['user_agent_parsed'] = ua_parsed

        # 3. Path canonicalization
        path_pattern = self.canonicalize_path(event['path'])
        enriched['path_pattern'] = path_pattern

        # 4. Endpoint discovery
        endpoint_id = await self.discover_endpoint(
            org_id=event['org_id'],
            app_id=event['app_id'],
            method=event['method'],
            path_pattern=path_pattern
        )
        enriched['endpoint_id'] = endpoint_id

        logger.debug(f"Enriched event: trace_id={event['trace_id']}")
        return enriched

    async def geoip_lookup(self, client_ip: str) -> Dict:
        """
        GeoIP lookup (placeholder).
        TODO: Integrate with MaxMind GeoIP2 or similar.
        """
        # Placeholder
        return {
            'country': 'US',
            'city': 'Unknown'
        }

    async def parse_user_agent(self, user_agent: str) -> Dict:
        """
        Parse User-Agent string.
        TODO: Integrate with user_agents library.
        """
        # Placeholder
        return {
            'browser': 'Unknown',
            'os': 'Unknown',
            'device': 'Unknown'
        }

    def canonicalize_path(self, path: str) -> str:
        """
        Canonicalize path to pattern.
        Example: /payments/charge/123 → /payments/charge/{id}

        Simple implementation: replace numeric segments with {id}, UUIDs with {uuid}.
        """
        import re

        # Replace UUIDs
        path_pattern = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{uuid}',
            path,
            flags=re.IGNORECASE
        )

        # Replace numeric IDs
        path_pattern = re.sub(r'/\d+', '/{id}', path_pattern)

        return path_pattern

    async def discover_endpoint(
        self,
        org_id: str,
        app_id: str,
        method: str,
        path_pattern: str
    ) -> str:
        """
        Discover or create endpoint in catalog.
        Returns endpoint_id.
        """
        from asgiref.sync import sync_to_async
        from core.models import APIEndpoint
        from uuid import UUID

        @sync_to_async
        def get_or_create_endpoint():
            endpoint, created = APIEndpoint.objects.get_or_create(
                org_id=UUID(org_id),
                app_id=UUID(app_id),
                method=method,
                path_pattern=path_pattern,
                defaults={
                    'first_seen': timezone.now(),
                    'last_seen': timezone.now(),
                    'request_count': 0
                }
            )

            if not created:
                # Update last_seen and count
                endpoint.last_seen = timezone.now()
                endpoint.request_count += 1
                endpoint.save(update_fields=['last_seen', 'request_count'])

            return str(endpoint.endpoint_id)

        from django.utils import timezone
        return await get_or_create_endpoint()


# Consumer instance
enrichment_consumer = EnrichmentConsumer()
