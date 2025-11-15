"""
Django management command to run detector consumer.
"""
import asyncio
import logging
from django.core.management.base import BaseCommand
from detection.consumer import detector_consumer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run Kafka detector consumer'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting detector consumer...'))

        try:
            asyncio.run(detector_consumer.consume())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Detector consumer stopped by user'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Detector consumer error: {e}'))
            raise
