"""
Django management command to run enrichment consumer.
"""
import asyncio
import logging
from django.core.management.base import BaseCommand
from core.kafka.consumers.enrichment import enrichment_consumer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run Kafka enrichment consumer'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting enrichment consumer...'))

        try:
            asyncio.run(enrichment_consumer.consume())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Enrichment consumer stopped by user'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Enrichment consumer error: {e}'))
            raise
