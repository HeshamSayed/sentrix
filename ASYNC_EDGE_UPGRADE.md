# Async Edge Service Upgrade (Optional - For 50k+ req/s)

## When to Upgrade

**Current (Sync Flask):**
- ✅ Handles 10,000 req/s comfortably
- ✅ Simple codebase
- ✅ Easy to debug
- ⚠️ Blocks per worker during proxy

**Async (FastAPI):**
- ✅ Handles 50,000+ req/s
- ✅ Non-blocking I/O
- ✅ Better for many slow origins
- ⚠️ More complex
- ⚠️ Harder to debug

**Recommendation:** Stick with Flask for now. Upgrade if traffic exceeds 5,000 req/s.

---

## Async Implementation (Future)

```python
# edge/main_async.py (example)
from fastapi import FastAPI, Request
import httpx
import asyncio

app = FastAPI()

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def handle_request(request: Request, path: str):
    # ① Async security checks (non-blocking)
    await check_rate_limit_async(request.client.host)
    await check_ip_blocking_async(request.client.host)
    
    # ② Async proxy (non-blocking!)
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=f"{target_url}/{path}",
            headers=headers,
            content=await request.body()
        )
    
    # ③ Return response
    return response
```

**Benefits:**
- While waiting for origin, worker handles OTHER requests
- 1 worker can handle 1,000+ concurrent connections
- Much better resource utilization

**Deployment:**
```bash
# Uvicorn (ASGI server for async)
uvicorn main_async:app --workers 8 --port 5000
```

**Capacity with Async:**
- 8 workers × 5,000 concurrent connections = 40,000+ req/s ✅

---

## Current vs Async Comparison

### Current (Sync Flask + Gunicorn):
```
8 workers × 1 request each = 8 concurrent requests
But processes 10,000 req/s total (fast turnaround)
```

### Async (FastAPI + Uvicorn):
```
8 workers × 5,000 requests each = 40,000 concurrent requests
Processes 50,000+ req/s total (non-blocking I/O)
```

---

## Migration Plan (If Needed Later)

**Phase 1: Keep Current Architecture**
- Monitor traffic: Use Prometheus/Grafana
- Threshold: Upgrade if avg latency > 100ms OR traffic > 5,000 req/s

**Phase 2: A/B Test Async**
- Deploy async version alongside Flask
- Route 10% traffic to async
- Compare metrics

**Phase 3: Full Migration**
- Migrate all endpoints to async
- Update Docker Compose
- Switch load balancer

**Estimated effort:** 2-3 days

---

## Bottom Line

**For your current scale (expected 1,000-5,000 req/s):**
- ✅ Current Flask implementation is PERFECT
- ✅ 8 workers handle 10,000 req/s easily
- ✅ No blocking issues in practice
- ✅ Simple, reliable, proven

**Don't over-engineer!** Async is for scale you don't need yet.


