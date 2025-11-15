"""
Detection consumer.
Reads enriched events from Kafka, runs detectors, creates detection events.
"""
import asyncio
import json
import logging
from typing import Optional
from aiokafka import AIOKafkaConsumer
from django.conf import settings
from django.utils import timezone
from asgiref.sync import sync_to_async

from core.kafka.producer import kafka_producer
from core.ml.deepseek_client import r1_client
from .detectors import run_all_detectors
from .models import DetectionEvent

logger = logging.getLogger(__name__)


class DetectorConsumer:
    """
    Detector consumer:
    - Reads from: enriched.events
    - Runs: All registered detectors
    - Calls: Deepseek-R1 for high-confidence threats
    - Writes to: detection.events topic and DetectionEvent table
    """

    def __init__(self):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.running = False

    async def start(self):
        """Start consumer"""
        self.consumer = AIOKafkaConsumer(
            settings.KAFKA_TOPICS['ENRICHED_EVENTS'],
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id='detector-group',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=False,
            max_poll_records=100,
        )

        await self.consumer.start()
        await kafka_producer.start()
        self.running = True
        logger.info("Detector consumer started")

    async def stop(self):
        """Stop consumer"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
        logger.info("Detector consumer stopped")

    async def consume(self):
        """Main consumer loop"""
        await self.start()

        try:
            while self.running:
                # Poll messages
                result = await self.consumer.getmany(timeout_ms=1000, max_records=100)

                for tp, messages in result.items():
                    logger.info(f"Processing {len(messages)} events from {tp.topic}")

                    for message in messages:
                        try:
                            event = message.value
                            await self.process_event(event)

                        except Exception as e:
                            logger.error(f"Error processing event: {e}", exc_info=True)

                    # Commit offset after batch
                    await self.consumer.commit()

        except Exception as e:
            logger.error(f"Detector consumer error: {e}", exc_info=True)
        finally:
            await self.stop()

    async def process_event(self, event: dict):
        """
        Process a single enriched event through all detectors.

        Args:
            event: Enriched event dict
        """
        org_id = event.get('org_id')
        app_id = event.get('app_id')
        trace_id = event.get('trace_id')

        logger.debug(f"Processing event: trace_id={trace_id}")

        # Run all detectors
        detector_results = run_all_detectors(event)

        if not detector_results:
            # No threats detected
            return

        logger.info(f"Detected {len(detector_results)} threat(s) in trace_id={trace_id}")

        # Process each detection
        for result in detector_results:
            # For high-confidence detections, get R1 explanation
            r1_explanation = None
            r1_score = None

            if result.confidence_score >= 0.7:
                # Call R1 for deeper analysis and explanation
                r1_result = await self.get_r1_analysis(event, result)
                if r1_result:
                    r1_explanation = r1_result
                    r1_score = r1_result.get('score')

            # Create detection event in database
            detection = await self.create_detection_event(
                event=event,
                result=result,
                r1_explanation=r1_explanation,
                r1_score=r1_score
            )

            # Publish to detection.events topic
            await kafka_producer.send_detection_event({
                'detection_id': str(detection.detection_id),
                'org_id': str(org_id),
                'app_id': str(app_id),
                'trace_id': trace_id,
                'detector_type': result.detector_type,
                'detector_name': result.detector_name,
                'severity': result.severity,
                'attack_type': result.attack_type,
                'confidence_score': float(result.confidence_score),
                'r1_score': float(r1_score) if r1_score else None,
                'detected_at': timezone.now().isoformat()
            })

    async def get_r1_analysis(self, event: dict, detector_result) -> Optional[dict]:
        """
        Get Deepseek-R1 analysis for a detection.

        Args:
            event: Original event
            detector_result: DetectorResult object

        Returns:
            R1 analysis dict or None
        """
        try:
            # Build features for R1
            features = {
                'method': event.get('method'),
                'path': event.get('path'),
                'client_ip': event.get('client_ip'),
                'detector_type': detector_result.detector_type,
                'detector_name': detector_result.detector_name,
                'attack_type': detector_result.attack_type,
                'evidence': detector_result.evidence,
                'initial_confidence': detector_result.confidence_score
            }

            # Call R1 (batch mode, longer timeout)
            r1_result = await r1_client.infer_batch(features)

            if r1_result.get('score') is not None:
                return {
                    'score': r1_result['score'],
                    'verdict': r1_result.get('verdict'),
                    'reasoning': r1_result.get('explanation', ''),
                    'evidence': detector_result.evidence,
                    'model_version': r1_result.get('model_version', 'r1-stub-v1')
                }

        except Exception as e:
            logger.error(f"Error getting R1 analysis: {e}", exc_info=True)

        return None

    @sync_to_async
    def create_detection_event(
        self,
        event: dict,
        result,
        r1_explanation: Optional[dict],
        r1_score: Optional[float]
    ) -> DetectionEvent:
        """
        Create DetectionEvent in database.

        Args:
            event: Original event
            result: DetectorResult
            r1_explanation: R1 analysis dict
            r1_score: R1 risk score

        Returns:
            Created DetectionEvent
        """
        from uuid import UUID

        detection = DetectionEvent.objects.create(
            org_id=UUID(event['org_id']),
            app_id=UUID(event['app_id']),
            endpoint_id=UUID(event['endpoint_id']) if event.get('endpoint_id') else None,
            trigger_event_ids=[],  # TODO: Get from event if available
            trace_ids=[event.get('trace_id')],
            detector_type=result.detector_type,
            detector_name=result.detector_name,
            severity=result.severity,
            confidence_score=result.confidence_score,
            r1_score=r1_score,
            r1_explanation=r1_explanation,
            attack_type=result.attack_type,
            client_ip=event.get('client_ip'),
            status='open'
        )

        logger.info(
            f"Created detection: {detection.detection_id} "
            f"(severity={detection.severity}, type={detection.attack_type})"
        )

        return detection


# Consumer instance
detector_consumer = DetectorConsumer()
