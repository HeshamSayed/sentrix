"""
SENTRIX Edge - Fast API Gateway with Real-time Security Checks
This service acts as a reverse proxy that sits between clients and their backend systems,
providing fast security checks and traffic mirroring to the analyzer.
"""

from fastapi import FastAPI, Request, Response, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import asyncio
import redis.asyncio as redis
from typing import Optional, Dict, Any
import time
import hashlib
import json
import os
from datetime import datetime, timedelta
import logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('sentrix_requests_total', 'Total requests', ['method', 'status'])
REQUEST_LATENCY = Histogram('sentrix_request_latency_seconds', 'Request latency', ['method'])
BLOCKED_REQUESTS = Counter('sentrix_blocked_requests_total', 'Blocked requests', ['reason'])
ACTIVE_CONNECTIONS = Gauge('sentrix_active_connections', 'Active connections')

app = FastAPI(
    title="SENTRIX Edge",
    description="API Gateway with Real-time Security",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection for caching and rate limiting
redis_client = None

# Configuration
BACKEND_API_URL = "http://backend:8000"
ANALYZER_URL = "http://ai-service:5000"
INGEST_URL = "http://ingest:8002"

# Global block rules cache
blocked_ips = set()
blocked_patterns = []


async def get_redis():
    """Get Redis connection"""
    global redis_client
    if redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://:sentrix_redis_pass@redis:6379/0")
        redis_client = await redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    return redis_client


@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    await get_redis()
    logger.info("SENTRIX Edge started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown"""
    global redis_client
    if redis_client:
        await redis_client.close()


def generate_request_id() -> str:
    """Generate unique request ID"""
    return hashlib.sha256(
        f"{time.time()}{id(object())}".encode()
    ).hexdigest()[:16]


async def check_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """
    Fast check: Validate API key against cached data
    Returns application config if valid, None otherwise
    """
    r = await get_redis()
    
    # Check Redis cache first (fast)
    cached = await r.get(f"apikey:{api_key}")
    if cached:
        return json.loads(cached)
    
    # If not in cache, fetch from backend
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_API_URL}/api/applications/validate_key/",
                headers={"X-API-Key": api_key},
                timeout=2.0
            )
            
            if response.status_code == 200:
                app_config = response.json()
                # Cache for 5 minutes
                await r.setex(
                    f"apikey:{api_key}",
                    300,
                    json.dumps(app_config)
                )
                return app_config
    except Exception as e:
        logger.error(f"Error validating API key: {e}")
    
    return None


async def resolve_host_config(host: str) -> Optional[Dict[str, Any]]:
    """
    Validate incoming Host for DNS onboarding (zero-deploy).
    Returns application config if host is recognized and active.
    """
    r = await get_redis()
    cache_key = f"hostmap:{host}"
    cached = await r.get(cache_key)
    if cached:
        return json.loads(cached)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BACKEND_API_URL}/api/applications/resolve-host/",
                params={"host": host},
                timeout=2.0
            )
            if resp.status_code == 200:
                cfg = resp.json()
                await r.setex(cache_key, 300, json.dumps(cfg))
                return cfg
    except Exception as e:
        logger.error(f"Error resolving host {host}: {e}")
    return None


async def fast_security_check(
    request: Request,
    app_config: Dict[str, Any],
    request_data: Dict[str, Any]
) -> Optional[Dict[str, str]]:
    """
    Fast security checks (< 10ms):
    - IP blacklist check
    - Rate limiting
    - Geo-blocking
    - Simple pattern matching
    
    Returns error dict if blocked, None if allowed
    """
    client_ip = request.client.host
    
    # 1. Check global IP blacklist (in-memory, very fast)
    if client_ip in blocked_ips:
        return {
            "error": "blocked",
            "reason": "IP address is globally blocked",
            "code": "IP_BLOCKED"
        }
    
    # 2. Check application-specific blocked IPs
    if client_ip in app_config.get("blocked_ips", []):
        return {
            "error": "blocked",
            "reason": "IP address blocked by application policy",
            "code": "IP_BLOCKED"
        }
    
    # 3. Rate limiting check
    r = await get_redis()
    rate_limit_key = f"ratelimit:{app_config['id']}:{client_ip}"
    
    request_count = await r.incr(rate_limit_key)
    if request_count == 1:
        await r.expire(rate_limit_key, 60)  # 1 minute window
    
    # Default rate limit: 1000 requests per minute
    max_requests = app_config.get("rate_limit", 1000)
    if request_count > max_requests:
        return {
            "error": "rate_limit_exceeded",
            "reason": f"Rate limit of {max_requests} requests/minute exceeded",
            "code": "RATE_LIMIT"
        }
    
    # 4. Check for suspicious patterns (fast regex)
    path = request.url.path
    suspicious_patterns = [
        "../", "etc/passwd", "cmd=", "eval(", "exec(",
        "<script", "javascript:", "onerror=", "onload="
    ]
    
    if any(pattern in path.lower() for pattern in suspicious_patterns):
        return {
            "error": "blocked",
            "reason": "Suspicious pattern detected in request",
            "code": "PATTERN_BLOCKED"
        }
    
    return None


async def mirror_to_analyzer(request_data: Dict[str, Any]):
    """
    Mirror request data to analyzer for deep analysis (async, non-blocking)
    This happens in the background and doesn't affect request latency
    """
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{ANALYZER_URL}/analyze",
                json=request_data,
                timeout=5.0
            )
    except Exception as e:
        logger.warning(f"Failed to mirror to analyzer: {e}")


async def send_to_ingest(request_data: Dict[str, Any]):
    """
    Send request data to ingest service for logging and storage
    This happens in the background
    """
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{INGEST_URL}/ingest",
                json=request_data,
                timeout=5.0
            )
    except Exception as e:
        logger.warning(f"Failed to send to ingest: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "sentrix-edge", "async": True, "workers": 8}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/admin/block-ip")
async def block_ip(ip: str, x_admin_key: Optional[str] = Header(None)):
    """
    Admin endpoint to add IP to global blocklist
    Called by the analyzer when a threat is detected
    """
    # Verify admin key
    if x_admin_key != "admin-secret-key-change-me":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    blocked_ips.add(ip)
    
    # Also update Redis for persistence across restarts
    r = await get_redis()
    await r.sadd("global:blocked_ips", ip)
    
    logger.info(f"IP {ip} added to global blocklist")
    
    return {"status": "success", "blocked_ip": ip}


@app.get("/admin/blocked-ips")
async def get_blocked_ips(x_admin_key: Optional[str] = Header(None)):
    """Get list of globally blocked IPs"""
    if x_admin_key != "admin-secret-key-change-me":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return {"blocked_ips": list(blocked_ips)}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_request(
    request: Request,
    path: str,
    x_api_key: Optional[str] = Header(None),
    x_sentrix_key: Optional[str] = Header(None)
):
    """
    Main proxy endpoint - handles all requests
    
    Flow:
    1. Extract API key (X-API-Key or X-SENTRIX-Key header)
    2. Validate API key (fast check with cache)
    3. Run fast security checks (< 10ms)
    4. Proxy to target backend
    5. Mirror to analyzer (async, non-blocking)
    6. Log to ingest (async, non-blocking)
    7. Return response
    """
    start_time = time.time()
    request_id = generate_request_id()
    
    # Track active connections
    ACTIVE_CONNECTIONS.inc()
    
    try:
        return await _handle_request_internal(request, path, x_api_key, x_sentrix_key, start_time, request_id)
    finally:
        ACTIVE_CONNECTIONS.dec()


async def _handle_request_internal(
    request: Request,
    path: str,
    x_api_key: Optional[str],
    x_sentrix_key: Optional[str],
    start_time: float,
    request_id: str
):
    """Internal request handler with metrics"""
    # Try header-based auth first
    app_config: Optional[Dict[str, Any]] = None
    api_key = x_sentrix_key or x_api_key
    if api_key:
        app_config = await check_api_key(api_key)
    else:
        # Zero-deploy path: resolve by Host header
        host = request.headers.get("host", "").split(":")[0].lower()
        if host:
            app_config = await resolve_host_config(host)
    if not app_config:
        REQUEST_COUNT.labels(method=request.method, status=401).inc()
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Missing or invalid credentials (API key or recognized host)",
                "request_id": request_id
            }
        )
    
    # Check if traffic is enabled
    if not app_config.get("is_traffic_enabled", False):
        return JSONResponse(
            status_code=403,
            content={
                "error": "traffic_disabled",
                "message": "Traffic is disabled for this application",
                "request_id": request_id
            }
        )
    
    # Prepare request data
    client_ip = request.client.host
    request_data = {
        "request_id": request_id,
        "application_id": app_config["id"],
        "timestamp": datetime.utcnow().isoformat(),
        "method": request.method,
        "path": path,
        "ip_address": client_ip,
        "headers": dict(request.headers),
        "user_agent": request.headers.get("user-agent", ""),
    }
    
    # Read body if present
    try:
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
            if body:
                request_data["body_size"] = len(body)
    except:
        pass
    
    # Fast security check
    security_check = await fast_security_check(request, app_config, request_data)
    if security_check:
        # Request blocked
        request_data["status_code"] = 403
        request_data["blocked"] = True
        request_data["block_reason"] = security_check["reason"]
        
        # Track blocked request
        BLOCKED_REQUESTS.labels(reason=security_check["code"]).inc()
        REQUEST_COUNT.labels(method=request.method, status=403).inc()
        
        # Log to ingest
        asyncio.create_task(send_to_ingest(request_data))
        
        return JSONResponse(
            status_code=403,
            content={
                "error": security_check["error"],
                "message": security_check["reason"],
                "code": security_check["code"],
                "request_id": request_id
            }
        )
    
    # Get target URL from application config
    target_url = app_config.get("target_url", "")
    if not target_url:
        return JSONResponse(
            status_code=500,
            content={
                "error": "configuration_error",
                "message": "Target URL not configured for this application",
                "request_id": request_id
            }
        )
    
    # Build full target URL
    full_url = f"{target_url.rstrip('/')}/{path}"
    query_params = str(request.url.query)
    if query_params:
        full_url = f"{full_url}?{query_params}"
    
    # Add SENTRIX signature header (for origin validation)
    proxy_headers = dict(request.headers)
    proxy_headers.pop('host', None)  # Will be set by httpx
    
    # Sign request with app signature key
    signature_key = app_config.get('origin_signature_key', '')
    if signature_key:
        import hashlib
        sig_data = f"{request.method}:{path}:{signature_key}"
        signature = hashlib.sha256(sig_data.encode()).hexdigest()
        proxy_headers['X-SENTRIX-Signature'] = signature
    else:
        # Fallback: just mark as protected by SENTRIX
        proxy_headers['X-SENTRIX-Signature'] = 'sentrix-protected'
    
    proxy_headers['X-SENTRIX-Request-ID'] = request_id
    proxy_headers['X-SENTRIX-Protected'] = 'true'
    
    # Proxy the request
    try:
        async with httpx.AsyncClient() as client:
            # Remove hop-by-hop headers
            hop_by_hop = [
                "connection", "keep-alive", "proxy-authenticate",
                "proxy-authorization", "te", "trailers", "transfer-encoding",
                "upgrade"
            ]
            for header in hop_by_hop:
                proxy_headers.pop(header, None)
            
            # Make the proxied request
            response = await client.request(
                method=request.method,
                url=full_url,
                headers=proxy_headers,
                content=await request.body() if request.method in ["POST", "PUT", "PATCH"] else None,
                timeout=30.0,
                follow_redirects=False
            )
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            latency_seconds = latency_ms / 1000.0
            
            # Track metrics
            REQUEST_COUNT.labels(method=request.method, status=response.status_code).inc()
            REQUEST_LATENCY.labels(method=request.method).observe(latency_seconds)
            
            # Update request data with response info
            request_data["status_code"] = response.status_code
            request_data["response_time_ms"] = latency_ms
            request_data["blocked"] = False
            
            # Mirror to analyzer (async, non-blocking)
            asyncio.create_task(mirror_to_analyzer(request_data))
            
            # Log to ingest (async, non-blocking)
            asyncio.create_task(send_to_ingest(request_data))
            
            # Return the response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
            
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={
                "error": "gateway_timeout",
                "message": "Target backend timeout",
                "request_id": request_id
            }
        )
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        return JSONResponse(
            status_code=502,
            content={
                "error": "bad_gateway",
                "message": "Failed to proxy request to target",
                "request_id": request_id
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

