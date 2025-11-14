# Sentrix API Guide

Complete API reference for Sentrix management APIs.

## Base URL

```
http://localhost:8000/v1
```

## Authentication

All endpoints (except `/auth/login` and `/edge/decision`) require JWT authentication.

### Login

```http
POST /v1/auth/login/
Content-Type: application/json

{
  "email": "admin@acme.com",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "user_id": "uuid",
    "email": "admin@acme.com",
    "full_name": "Admin User",
    "role": "admin",
    "org": "org-uuid",
    "org_name": "Acme Corporation"
  }
}
```

### Using the Token

Include the access token in all subsequent requests:

```http
GET /v1/organizations/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

---

## Organizations

### List Organizations

```http
GET /v1/organizations/
Authorization: Bearer <token>
```

**Response:**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "org_id": "uuid",
      "name": "Acme Corporation",
      "slug": "acme-corp",
      "default_config": {
        "rate_limit_rpm": 1000,
        "enable_r1_realtime": true
      },
      "created_at": "2025-11-14T12:00:00Z",
      "updated_at": "2025-11-14T12:00:00Z"
    }
  ]
}
```

### Get Organization

```http
GET /v1/organizations/{org_id}/
Authorization: Bearer <token>
```

### Update Organization Config

```http
PATCH /v1/organizations/{org_id}/update_config/
Authorization: Bearer <token>
Content-Type: application/json

{
  "rate_limit_rpm": 2000,
  "enable_r1_batch": true
}
```

**Response:**
```json
{
  "message": "Configuration updated",
  "default_config": {
    "rate_limit_rpm": 2000,
    "enable_r1_realtime": true,
    "enable_r1_batch": true
  }
}
```

### Get Quota Summary

```http
GET /v1/organizations/{org_id}/quota_summary/
Authorization: Bearer <token>
```

**Response:**
```json
{
  "applications": {
    "quota_type": "applications",
    "current": 2,
    "limit": 5,
    "available": 3,
    "can_create": true
  },
  "users": {
    "quota_type": "users",
    "current": 3,
    "limit": 20,
    "available": 17,
    "can_create": true
  },
  "requests": {
    "quota_type": "requests_per_month",
    "current": 125000,
    "limit": 10000000,
    "available": 9875000,
    "can_process": true,
    "period_start": "2025-11-01T00:00:00Z"
  }
}
```

---

## Subscriptions

### Get Current Subscription

```http
GET /v1/subscriptions/current/
Authorization: Bearer <token>
```

**Response:**
```json
{
  "subscription_id": "uuid",
  "org": "org-uuid",
  "org_name": "Acme Corporation",
  "plan_tier": "pro",
  "quota_max_applications": 5,
  "quota_max_users": 20,
  "quota_requests_per_month": 10000000,
  "features": {
    "r1_realtime": true,
    "r1_batch": true,
    "threat_hunting": true
  },
  "valid_from": "2025-11-01T00:00:00Z",
  "valid_until": null,
  "is_active": true
}
```

### List Subscriptions

```http
GET /v1/subscriptions/
Authorization: Bearer <token>
```

---

## Applications

### List Applications

```http
GET /v1/applications/
Authorization: Bearer <token>
```

**Response:**
```json
{
  "count": 2,
  "results": [
    {
      "app_id": "uuid",
      "org": "org-uuid",
      "org_name": "Acme Corporation",
      "name": "Payment API",
      "slug": "payment-api",
      "domain": "api.acme-payments.com",
      "origin_url": "https://backend-payments.acme.com",
      "cname_target": "sentrix-edge-us-east.example.com",
      "verification_token": "uuid",
      "dns_verified": true,
      "dns_verified_at": "2025-11-14T12:00:00Z",
      "custom_config": {
        "rate_limit_rpm": 5000
      },
      "merged_config": {
        "rate_limit_rpm": 5000,
        "enable_r1_realtime": true
      },
      "failover_mode": "fail_open",
      "is_active": true,
      "created_at": "2025-11-14T12:00:00Z",
      "updated_at": "2025-11-14T12:00:00Z"
    }
  ]
}
```

### Create Application

```http
POST /v1/applications/
Authorization: Bearer <token>
Content-Type: application/json

{
  "org": "org-uuid",
  "name": "New API",
  "slug": "new-api",
  "domain": "api.new.com",
  "origin_url": "https://backend.new.com",
  "custom_config": {
    "rate_limit_rpm": 3000
  },
  "failover_mode": "fail_open"
}
```

**Quota Enforcement:** Will return 403 if quota exceeded.

### Get Application

```http
GET /v1/applications/{app_id}/
Authorization: Bearer <token>
```

### Get Application Config

```http
GET /v1/applications/{app_id}/config/
Authorization: Bearer <token>
```

**Response:**
```json
{
  "org_default_config": {
    "rate_limit_rpm": 1000,
    "enable_r1_realtime": true
  },
  "app_custom_config": {
    "rate_limit_rpm": 5000,
    "enable_captcha": true
  },
  "merged_config": {
    "rate_limit_rpm": 5000,
    "enable_r1_realtime": true,
    "enable_captcha": true
  }
}
```

### Update Application Config

```http
PATCH /v1/applications/{app_id}/update_config/
Authorization: Bearer <token>
Content-Type: application/json

{
  "rate_limit_rpm": 7000,
  "custom_rule": "value"
}
```

**Effect:** Invalidates Redis cache, merges with existing custom_config.

### Verify DNS

```http
POST /v1/applications/{app_id}/verify_dns/
Authorization: Bearer <token>
```

---

## Users

### List Users

```http
GET /v1/users/
Authorization: Bearer <token>
```

**Response:**
```json
{
  "count": 3,
  "results": [
    {
      "user_id": "uuid",
      "org": "org-uuid",
      "org_name": "Acme Corporation",
      "email": "admin@acme.com",
      "full_name": "Admin User",
      "role": "admin",
      "is_active": true,
      "last_login": "2025-11-14T12:00:00Z",
      "created_at": "2025-11-14T12:00:00Z",
      "updated_at": "2025-11-14T12:00:00Z"
    }
  ]
}
```

### Create User

```http
POST /v1/users/
Authorization: Bearer <token>
Content-Type: application/json

{
  "org": "org-uuid",
  "email": "newuser@acme.com",
  "password": "securepassword",
  "full_name": "New User",
  "role": "analyst"
}
```

**Quota Enforcement:** Will return 403 if user quota exceeded.

### Get User

```http
GET /v1/users/{user_id}/
Authorization: Bearer <token>
```

### Get User Permissions

```http
GET /v1/users/{user_id}/permissions/
Authorization: Bearer <token>
```

**Response:**
```json
{
  "role": "analyst",
  "permissions": [
    "view_events",
    "view_endpoints",
    "view_detections",
    "create_policy",
    "update_policy"
  ]
}
```

---

## API Endpoints (Catalog)

### List Discovered Endpoints

```http
GET /v1/endpoints/?app_id={app_id}
Authorization: Bearer <token>
```

**Query Parameters:**
- `app_id` (optional): Filter by application

**Response:**
```json
{
  "count": 15,
  "results": [
    {
      "endpoint_id": "uuid",
      "org": "org-uuid",
      "org_name": "Acme Corporation",
      "app": "app-uuid",
      "app_name": "Payment API",
      "method": "POST",
      "path_pattern": "/payments/charge/{id}",
      "request_schema": {...},
      "response_schema": {...},
      "owner": "payments-team",
      "tags": ["payment", "critical"],
      "risk_score": 0.75,
      "first_seen": "2025-11-01T00:00:00Z",
      "last_seen": "2025-11-14T12:00:00Z",
      "request_count": 125000
    }
  ]
}
```

### Get Endpoint

```http
GET /v1/endpoints/{endpoint_id}/
Authorization: Bearer <token>
```

---

## Usage Tracking

### List Usage

```http
GET /v1/usage/?app_id={app_id}&period_start__gte=2025-11-01
Authorization: Bearer <token>
```

**Query Parameters:**
- `app_id` (optional): Filter by application
- `period_start__gte` (optional): Filter by period start >= date
- `period_start__lte` (optional): Filter by period start <= date

**Response:**
```json
{
  "count": 5,
  "results": [
    {
      "usage_id": "uuid",
      "org": "org-uuid",
      "org_name": "Acme Corporation",
      "app": "app-uuid",
      "app_name": "Payment API",
      "period_start": "2025-11-14T00:00:00Z",
      "period_end": "2025-11-15T00:00:00Z",
      "request_count": 125000,
      "blocked_count": 45,
      "r1_invocation_count": 1200
    }
  ]
}
```

---

## Decision API (Edge)

### Make Decision

```http
POST /v1/edge/decision
Content-Type: application/json

{
  "domain": "api.acme-payments.com",
  "method": "POST",
  "path": "/payments/charge/123",
  "client_ip": "1.2.3.4",
  "headers": {...},
  "body_hash": "sha256..."
}
```

**No authentication required** (called by edge proxy).

**Response:**
```json
{
  "action": "allow",
  "reason": "no_threats_detected",
  "score": 0.1,
  "explanation": "Request passed all checks",
  "cache_ttl": 60
}
```

**Possible actions:**
- `allow` - Allow request
- `block` - Block request
- `throttle` - Rate limit exceeded
- `challenge` - Require CAPTCHA/challenge

---

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden (Quota Exceeded)

```json
{
  "error": "quota_exceeded",
  "message": "Application quota exceeded. Current: 5, Limit: 5",
  "quota_type": "applications",
  "current": 5,
  "limit": 5
}
```

### 404 Not Found

```json
{
  "detail": "Not found."
}
```

### 400 Bad Request

```json
{
  "field_name": ["Error message"]
}
```

---

## Rate Limiting

Not yet implemented. Future: 1000 requests per minute per user.

---

## Pagination

All list endpoints support pagination:

```http
GET /v1/applications/?limit=10&offset=20
```

**Response:**
```json
{
  "count": 100,
  "next": "http://localhost:8000/v1/applications/?limit=10&offset=30",
  "previous": "http://localhost:8000/v1/applications/?limit=10&offset=10",
  "results": [...]
}
```

---

## Testing

```bash
# Create test data
docker-compose exec control-plane python manage.py create_test_data

# Run API tests
./test_api.sh
```

---

## Default Test Users

After running `create_test_data`:

| Email | Password | Role |
|-------|----------|------|
| admin@acme.com | admin123 | admin |
| analyst@acme.com | analyst123 | analyst |
| viewer@acme.com | viewer123 | viewer |

---

## Postman Collection

Import the following base URL and create requests as needed:
- Base URL: `http://localhost:8000/v1`
- Environment variable: `token` (set after login)

---

## WebSocket APIs (Future)

- `/ws/events/` - Real-time event stream
- `/ws/detections/` - Real-time detection alerts

Not yet implemented.

---

## Detection Events (Phase 4)

### List Detections

```http
GET /v1/detection/detections/?app_id={app_id}&severity={severity}&status={status}
Authorization: Bearer <token>
```

**Query Parameters:**
- `app_id` (optional): Filter by application
- `severity` (optional): Filter by severity (info, low, medium, high, critical)
- `status` (optional): Filter by status (open, investigating, confirmed, false_positive, resolved)
- `detector_type` (optional): Filter by detector type
- `attack_type` (optional): Filter by attack type

**Response:**
```json
{
  "count": 45,
  "results": [
    {
      "detection_id": "uuid",
      "org": "org-uuid",
      "org_name": "Acme Corporation",
      "app": "app-uuid",
      "app_name": "Payment API",
      "endpoint": "endpoint-uuid",
      "endpoint_path": "POST /payments/charge/{id}",
      "trigger_event_ids": [12345, 12346],
      "trace_ids": ["trace-123"],
      "detector_type": "r1_realtime",
      "detector_name": "SQL Injection Detector",
      "severity": "high",
      "confidence_score": 0.95,
      "r1_score": 0.89,
      "r1_explanation": {
        "reasoning": "...",
        "evidence": [...],
        "model_version": "r1-distill-v1"
      },
      "attack_type": "sqli",
      "client_ip": "1.2.3.4",
      "status": "open",
      "assigned_to": null,
      "assigned_to_email": null,
      "detected_at": "2025-11-14T12:00:00Z",
      "created_at": "2025-11-14T12:00:00Z",
      "updated_at": "2025-11-14T12:00:00Z"
    }
  ]
}
```

### Get Detection

```http
GET /v1/detection/detections/{detection_id}/
Authorization: Bearer <token>
```

### Get Detection Summary

```http
GET /v1/detection/detections/summary/?app_id={app_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "total": 45,
  "open": 12,
  "investigating": 8,
  "confirmed": 5,
  "false_positive": 3,
  "resolved": 17,
  "by_severity": {
    "critical": 3,
    "high": 8,
    "medium": 15,
    "low": 12,
    "info": 7
  },
  "by_detector_type": {
    "rule_based": 20,
    "statistical": 10,
    "r1_realtime": 12,
    "r1_batch": 3
  },
  "recent_detections": [...]
}
```

### Assign Detection

```http
POST /v1/detection/detections/{detection_id}/assign/
Authorization: Bearer <token>
Content-Type: application/json

{
  "assigned_to": "user-uuid"
}
```

**Effect:** Assigns detection to user and changes status to "investigating" if currently "open".

### Close Detection

```http
POST /v1/detection/detections/{detection_id}/close/
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "resolved",
  "notes": "False alarm - legitimate traffic"
}
```

**Status options:**
- `resolved` - Threat was real and resolved
- `false_positive` - Not actually a threat

### Update Detection

```http
PATCH /v1/detection/detections/{detection_id}/
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "investigating",
  "assigned_to": "user-uuid"
}
```

---

## Dashboard (Phase 4)

### Get Dashboard Summary

```http
GET /v1/dashboard/summary/?app_id={app_id}&hours={hours}
Authorization: Bearer <token>
```

**Query Parameters:**
- `app_id` (optional): Filter by application
- `hours` (optional): Time window in hours (default: 24)

**Response:**
```json
{
  "overview": {
    "total_applications": 5,
    "total_users": 12,
    "total_endpoints": 150
  },
  "traffic": {
    "requests_24h": 125000,
    "blocked_24h": 450,
    "block_rate": 0.36,
    "r1_invocations_24h": 1200
  },
  "detections": {
    "total": 45,
    "open": 12,
    "investigating": 8,
    "critical": 3,
    "high": 8,
    "medium": 15,
    "by_severity": {...},
    "by_status": {...},
    "recent": [...]
  },
  "quota": {
    "applications": {
      "current": 5,
      "limit": 10,
      "available": 5,
      "usage_percent": 50.0
    },
    "users": {
      "current": 12,
      "limit": 20,
      "available": 8,
      "usage_percent": 60.0
    },
    "requests": {
      "current": 2500000,
      "limit": 10000000,
      "available": 7500000,
      "usage_percent": 25.0,
      "period_start": "2025-11-01T00:00:00Z"
    }
  },
  "period_hours": 24
}
```

### Get Metrics Time Series

```http
GET /v1/dashboard/metrics/?app_id={app_id}&metric={metric}&start={start}&end={end}&interval={interval}
Authorization: Bearer <token>
```

**Query Parameters:**
- `app_id` (optional): Filter by application
- `metric`: Metric name (requests, blocked, detections, latency)
- `start`: Start time (ISO 8601)
- `end`: End time (ISO 8601)
- `interval`: Grouping interval (hour, day)

**Response:**
```json
{
  "metric": "requests",
  "interval": "hour",
  "start": "2025-11-14T00:00:00Z",
  "end": "2025-11-15T00:00:00Z",
  "data": [
    {"timestamp": "2025-11-14T00:00:00Z", "value": 1250},
    {"timestamp": "2025-11-14T01:00:00Z", "value": 1180},
    {"timestamp": "2025-11-14T02:00:00Z", "value": 1320}
  ]
}
```

---

## Phase 4 Complete

New endpoints added:
- ✅ Detection management (list, get, assign, close, summary)
- ✅ Dashboard summary (overview, traffic, detections, quota)
- ✅ Metrics time-series (placeholder for charts)

All endpoints enforce data isolation by org_id and optional app_id filtering.
