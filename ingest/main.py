from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
import orjson
import redis
import logging
from confluent_kafka import Producer
import os
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Sentrix Ingest API",
    description="High-throughput API traffic ingestion service",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis
redis_url = os.getenv('REDIS_URL', 'redis://:sentrix_redis_pass@redis:6379/1')
redis_client = redis.from_url(redis_url, decode_responses=False)

# Initialize Kafka Producer
kafka_conf = {
    'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
    'client.id': 'sentrix-ingest',
}
kafka_producer = Producer(kafka_conf)

# Pydantic models
class APIRequestLog(BaseModel):
    """API Request log entry"""
    environment_id: str
    method: str
    path: str
    query_params: Optional[Dict[str, Any]] = {}
    headers: Optional[Dict[str, str]] = {}
    
    ip_address: str
    user_agent: Optional[str] = None
    country_code: Optional[str] = None
    
    status_code: int
    response_time_ms: int
    
    request_body: Optional[Dict[str, Any]] = None
    response_body: Optional[Dict[str, Any]] = None
    
    timestamp: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BulkIngestRequest(BaseModel):
    """Bulk ingest multiple requests"""
    requests: List[APIRequestLog] = Field(..., max_items=1000)

class IngestResponse(BaseModel):
    """Ingest response"""
    success: bool
    request_id: str
    message: str

# Helper functions
def delivery_report(err, msg):
    """Kafka delivery callback"""
    if err is not None:
        logger.error(f'Message delivery failed: {err}')
    else:
        logger.debug(f'Message delivered to {msg.topic()} [{msg.partition()}]')

def publish_to_kafka(topic: str, key: str, value: dict):
    """Publish message to Kafka"""
    try:
        kafka_producer.produce(
            topic,
            key=key.encode('utf-8'),
            value=orjson.dumps(value),
            callback=delivery_report
        )
        kafka_producer.poll(0)
    except Exception as e:
        logger.error(f"Failed to publish to Kafka: {e}")
        raise

def check_rate_limit(api_key: str) -> bool:
    """Check rate limit for API key"""
    key = f"rate_limit:{api_key}"
    try:
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, 3600)  # 1 hour window
        
        # Max 10000 requests per hour
        if count > 10000:
            return False
        return True
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        return True  # Fail open

# API Endpoints
@app.get("/")
async def root():
    """Health check"""
    return {"status": "ok", "service": "sentrix-ingest"}

@app.get("/health")
async def health():
    """Detailed health check"""
    health_status = {
        "status": "ok",
        "redis": "unknown",
        "kafka": "unknown"
    }
    
    # Check Redis
    try:
        redis_client.ping()
        health_status["redis"] = "ok"
    except Exception as e:
        health_status["redis"] = "error"
        health_status["status"] = "degraded"
    
    # Check Kafka (basic check)
    try:
        # Just check if producer is initialized
        if kafka_producer:
            health_status["kafka"] = "ok"
    except Exception as e:
        health_status["kafka"] = "error"
        health_status["status"] = "degraded"
    
    return health_status

@app.post("/ingest", response_model=IngestResponse)
async def ingest_request(
    request_log: APIRequestLog,
    x_api_key: Optional[str] = Header(None)
):
    """
    Ingest a single API request log
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # Check rate limit
    if not check_rate_limit(x_api_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Generate request ID
    request_id = str(uuid.uuid4())
    
    # Add timestamp if not provided
    if not request_log.timestamp:
        request_log.timestamp = datetime.utcnow()
    
    # Prepare data
    data = request_log.model_dump()
    data['request_id'] = request_id
    data['ingested_at'] = datetime.utcnow().isoformat()
    
    # Publish to Kafka
    try:
        publish_to_kafka(
            topic='api-requests',
            key=request_log.environment_id,
            value=data
        )
        
        # Cache in Redis for real-time access (TTL 1 hour)
        cache_key = f"request:{request_id}"
        redis_client.setex(
            cache_key,
            3600,
            orjson.dumps(data)
        )
        
        return IngestResponse(
            success=True,
            request_id=request_id,
            message="Request ingested successfully"
        )
    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail="Ingest failed")

@app.post("/ingest/bulk", response_model=IngestResponse)
async def ingest_bulk(
    bulk_request: BulkIngestRequest,
    x_api_key: Optional[str] = Header(None)
):
    """
    Ingest multiple API request logs in bulk
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # Check rate limit
    if not check_rate_limit(x_api_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    batch_id = str(uuid.uuid4())
    ingested_count = 0
    
    for request_log in bulk_request.requests:
        try:
            request_id = str(uuid.uuid4())
            
            if not request_log.timestamp:
                request_log.timestamp = datetime.utcnow()
            
            data = request_log.model_dump()
            data['request_id'] = request_id
            data['batch_id'] = batch_id
            data['ingested_at'] = datetime.utcnow().isoformat()
            
            # Publish to Kafka
            publish_to_kafka(
                topic='api-requests',
                key=request_log.environment_id,
                value=data
            )
            
            ingested_count += 1
        except Exception as e:
            logger.error(f"Failed to ingest request in bulk: {e}")
    
    # Flush Kafka producer
    kafka_producer.flush()
    
    return IngestResponse(
        success=True,
        request_id=batch_id,
        message=f"Bulk ingest completed: {ingested_count}/{len(bulk_request.requests)} requests"
    )

@app.get("/stats")
async def get_stats():
    """Get ingestion statistics"""
    try:
        # Get some basic stats from Redis
        stats = {
            "redis_keys": redis_client.dbsize(),
            "uptime": "running"
        }
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

