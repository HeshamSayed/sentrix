#!/usr/bin/env python3
"""
SENTRIX Stream Processor
Consumes security events from Kafka and triggers AI analysis
"""

import json
import logging
import os
import asyncio
from typing import Dict, Any
from kafka import KafkaConsumer, KafkaProducer
import httpx
import redis.asyncio as redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
REDIS_URL = os.getenv('REDIS_URL', 'redis://:sentrix_redis_pass@redis:6379/0')
AI_SERVICE_URL = os.getenv('AI_SERVICE_URL', 'http://ai-service:5000')

# Topics
SECURITY_EVENTS_TOPIC = 'security-events'
AI_ANALYSIS_TOPIC = 'ai-analysis-results'

# Analysis thresholds
SUSPICIOUS_PATTERNS = [
    'sql injection',
    'xss',
    'command injection',
    'path traversal',
    'rate limit exceeded',
    'unusual pattern'
]


class SecurityStreamProcessor:
    """Processes security events and triggers AI analysis"""
    
    def __init__(self):
        self.consumer = KafkaConsumer(
            SECURITY_EVENTS_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id='sentrix-stream-processor',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=True
        )
        
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        
        self.redis_client = None
        logger.info("Stream processor initialized")
    
    async def get_redis(self):
        """Get async Redis connection"""
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client
    
    def should_analyze(self, event: Dict[str, Any]) -> bool:
        """Determine if event needs AI analysis"""
        # Always analyze blocked requests
        if event.get('blocked', False):
            return True
        
        # Check for suspicious patterns
        path = event.get('path', '').lower()
        for pattern in SUSPICIOUS_PATTERNS:
            if pattern in path:
                return True
        
        # Analyze high-risk endpoints
        if event.get('is_sensitive', False):
            return True
        
        # Random sampling for baseline (10% of normal traffic)
        return hash(event.get('request_id', '')) % 10 == 0
    
    async def trigger_ai_analysis(self, event: Dict[str, Any]):
        """Send event to AI service for deep analysis"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{AI_SERVICE_URL}/analyze",
                    json=event
                )
                
                if response.status_code == 200:
                    analysis = response.json()
                    
                    # Publish analysis results to Kafka
                    self.producer.send(
                        AI_ANALYSIS_TOPIC,
                        value={
                            'request_id': event.get('request_id'),
                            'analysis': analysis,
                            'timestamp': event.get('timestamp')
                        }
                    )
                    
                    # Cache high-risk IPs
                    if analysis.get('risk_score', 0) > 0.8:
                        r = await self.get_redis()
                        ip = event.get('ip_address')
                        await r.setex(
                            f"high_risk_ip:{ip}",
                            3600,  # 1 hour
                            json.dumps(analysis)
                        )
                        logger.warning(f"High-risk IP detected: {ip} (score: {analysis.get('risk_score')})")
                    
                    logger.info(f"AI analysis completed for request {event.get('request_id')}")
                else:
                    logger.error(f"AI service error: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Failed to analyze event: {e}")
    
    async def process_event(self, event: Dict[str, Any]):
        """Process a single security event"""
        try:
            # Check if analysis needed
            if self.should_analyze(event):
                logger.info(f"Triggering AI analysis for request {event.get('request_id')}")
                await self.trigger_ai_analysis(event)
            
            # Update metrics
            r = await self.get_redis()
            await r.incr('stream_processor:events_processed')
            
            if event.get('blocked', False):
                await r.incr('stream_processor:threats_detected')
        
        except Exception as e:
            logger.error(f"Error processing event: {e}")
    
    async def run(self):
        """Main processing loop"""
        logger.info("Starting stream processor...")
        
        try:
            while True:
                # Poll for messages
                message_batch = self.consumer.poll(timeout_ms=1000)
                
                if not message_batch:
                    await asyncio.sleep(0.1)
                    continue
                
                # Process messages concurrently
                tasks = []
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        event = message.value
                        tasks.append(self.process_event(event))
                
                if tasks:
                    await asyncio.gather(*tasks)
                    logger.info(f"Processed {len(tasks)} events")
        
        except KeyboardInterrupt:
            logger.info("Shutting down processor...")
        
        finally:
            self.consumer.close()
            self.producer.close()
            if self.redis_client:
                await self.redis_client.close()


if __name__ == "__main__":
    processor = SecurityStreamProcessor()
    asyncio.run(processor.run())

