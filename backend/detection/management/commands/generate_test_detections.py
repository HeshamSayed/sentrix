"""
Django management command to generate test detections.
Creates sample events with attack patterns for testing.
"""
import asyncio
import json
import logging
from uuid import uuid4
from django.core.management.base import BaseCommand
from django.utils import timezone
from aiokafka import AIOKafkaProducer
from django.conf import settings

from core.models import Organization, Application

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate test detections by publishing events with attack patterns'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of test events to generate'
        )

    def handle(self, *args, **options):
        count = options['count']
        self.stdout.write(self.style.SUCCESS(f'Generating {count} test detection events...'))

        asyncio.run(self.generate_events(count))

        self.stdout.write(self.style.SUCCESS(f'✓ Generated {count} test events'))
        self.stdout.write('')
        self.stdout.write('Events published to Kafka topic: enriched.events')
        self.stdout.write('The detector consumer will process them and create detections.')
        self.stdout.write('')
        self.stdout.write('To view detections:')
        self.stdout.write('  - Dashboard: GET /v1/dashboard/summary/')
        self.stdout.write('  - Detections: GET /v1/detection/detections/')
        self.stdout.write('  - Django Admin: http://localhost:8000/admin/detection/detectionevent/')

    async def generate_events(self, count: int):
        """Generate and publish test events with attack patterns"""

        # Get first org and app
        org = Organization.objects.first()
        app = Application.objects.filter(org=org).first()

        if not org or not app:
            self.stdout.write(self.style.ERROR('No organization or application found. Run create_test_data first.'))
            return

        self.stdout.write(f'Using org: {org.name}, app: {app.name}')

        # Connect to Kafka
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

        await producer.start()

        try:
            # Generate different types of attack events
            attack_patterns = [
                # SQL Injection
                {
                    'type': 'sqli',
                    'path': '/api/users',
                    'query_params': {'id': "1' OR '1'='1"},
                    'severity': 'high'
                },
                {
                    'type': 'sqli',
                    'path': '/api/products',
                    'query_params': {'search': "'; DROP TABLE users--"},
                    'severity': 'critical'
                },
                # XSS
                {
                    'type': 'xss',
                    'path': '/api/comments',
                    'body': {'text': '<script>alert("XSS")</script>'},
                    'severity': 'medium'
                },
                {
                    'type': 'xss',
                    'path': '/api/profile',
                    'body': {'bio': '<img src=x onerror=alert(1)>'},
                    'severity': 'medium'
                },
                # Suspicious paths
                {
                    'type': 'suspicious_path',
                    'path': '/admin/config',
                    'query_params': {},
                    'severity': 'medium'
                },
                {
                    'type': 'suspicious_path',
                    'path': '/.env',
                    'query_params': {},
                    'severity': 'high'
                },
            ]

            for i in range(count):
                # Pick attack pattern (cycle through)
                pattern = attack_patterns[i % len(attack_patterns)]

                # Create enriched event
                event = {
                    'org_id': str(org.org_id),
                    'app_id': str(app.app_id),
                    'trace_id': f'trace-test-{uuid4()}',
                    'timestamp': timezone.now().isoformat(),
                    'method': 'GET' if pattern['type'] == 'suspicious_path' else 'POST',
                    'path': pattern['path'],
                    'path_pattern': pattern['path'],
                    'client_ip': f'192.168.1.{(i % 254) + 1}',
                    'user_agent': 'Mozilla/5.0 (Test)',
                    'geo_country': 'US',
                    'geo_city': 'TestCity',
                    'endpoint_id': None,  # Would be set by enrichment in real flow
                    'request_meta': {
                        'query_params': pattern.get('query_params', {}),
                        'body': pattern.get('body', {}),
                        'headers': {
                            'user-agent': 'Mozilla/5.0 (Test)',
                            'accept': 'application/json'
                        }
                    },
                    'response_meta': {
                        'status': 200
                    }
                }

                # Publish to enriched.events topic
                await producer.send(
                    settings.KAFKA_TOPICS['ENRICHED_EVENTS'],
                    value=event,
                    key=event['org_id'].encode('utf-8')
                )

                self.stdout.write(f'  {i+1}. Published {pattern["type"]} event: {pattern["path"]}')

        finally:
            await producer.stop()
