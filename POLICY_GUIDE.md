# Sentrix Policy Engine - Quick Start Guide

Complete guide to creating, testing, and deploying security policies in Sentrix.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Policy Workflow](#policy-workflow)
3. [Creating Your First Policy](#creating-your-first-policy)
4. [Testing Policies](#testing-policies)
5. [Running Simulations](#running-simulations)
6. [Deploying to Production](#deploying-to-production)
7. [Common Policy Patterns](#common-policy-patterns)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

1. **Sentrix running locally:**
   ```bash
   docker compose up -d
   ```

2. **Test data created:**
   ```bash
   docker compose exec control-plane python manage.py create_test_data
   ```

3. **Get authentication token:**
   ```bash
   curl -X POST http://localhost:8000/v1/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"email": "admin@acme.com", "password": "admin123"}' \
     | jq -r '.access_token' > token.txt

   export TOKEN=$(cat token.txt)
   ```

### Create Example Policies

```bash
docker compose exec control-plane python manage.py create_example_policies
```

This creates 8 example policies in **observe mode** and **disabled** state.

---

## Policy Workflow

### Best Practice Workflow

```
1. CREATE        → Policy in observe mode, disabled
2. TEST          → Test DSL with sample events (/v1/policy/test/)
3. ENABLE        → Enable policy (still in observe mode)
4. MONITOR       → Check logs for matches (no blocking yet)
5. SIMULATE      → Run simulation against historical data
6. REVIEW        → Review simulation results and sample matches
7. ENFORCE       → Switch to enforce mode if acceptable
8. MONITOR       → Watch for false positives
9. ADJUST        → Fine-tune conditions or priority as needed
```

---

## Creating Your First Policy

### Example: Block Admin Access from External IPs

**Step 1: Create the Policy**

```bash
curl -X POST http://localhost:8000/v1/policy/policies/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Block External Admin Access",
    "description": "Only allow admin access from corporate network",
    "app_id": null,
    "condition": {
      "and": [
        {"field": "path", "op": "startswith", "value": "/admin"},
        {
          "not": {
            "field": "client_ip",
            "op": "in_cidr",
            "value": "10.0.0.0/8"
          }
        }
      ]
    },
    "action": {
      "type": "block",
      "response_code": 403,
      "message": "Admin access restricted to internal network"
    },
    "mode": "observe",
    "priority": 10
  }' | jq
```

**Response:**
```json
{
  "policy_id": "uuid",
  "name": "Block External Admin Access",
  "mode": "observe",
  "is_enabled": false,
  ...
}
```

Save the `policy_id` for next steps.

---

## Testing Policies

### Test DSL Before Creating

Use the `/v1/policy/test/` endpoint to validate your DSL:

```bash
curl -X POST http://localhost:8000/v1/policy/test/ \
  -H "Content-Type: application/json" \
  -d '{
    "condition": {
      "and": [
        {"field": "path", "op": "startswith", "value": "/admin"},
        {
          "not": {
            "field": "client_ip",
            "op": "in_cidr",
            "value": "10.0.0.0/8"
          }
        }
      ]
    },
    "events": [
      {
        "method": "GET",
        "path": "/admin/users",
        "client_ip": "203.0.113.50"
      },
      {
        "method": "GET",
        "path": "/admin/users",
        "client_ip": "10.0.0.5"
      },
      {
        "method": "GET",
        "path": "/api/users",
        "client_ip": "203.0.113.50"
      }
    ]
  }' | jq
```

**Expected Output:**
```json
{
  "condition": {...},
  "results": [
    {"event": {...}, "matches": true},   // External IP on /admin
    {"event": {...}, "matches": false},  // Internal IP on /admin
    {"event": {...}, "matches": false}   // External IP on /api
  ],
  "total_events": 3,
  "matched": 1
}
```

---

## Running Simulations

### Enable Policy First

```bash
curl -X POST http://localhost:8000/v1/policy/policies/{policy_id}/enable/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Run Simulation (7 days)

```bash
curl -X POST http://localhost:8000/v1/policy/policies/{policy_id}/simulate/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"days": 7}' | jq
```

**Response:**
```json
{
  "policy_id": "uuid",
  "policy_name": "Block External Admin Access",
  "simulation": {
    "date_range": {
      "start": "2025-11-07T00:00:00Z",
      "end": "2025-11-14T00:00:00Z",
      "days": 7
    },
    "total_requests_analyzed": 10000,
    "total_requests_in_period": 125000,
    "sampled": true,
    "affected_requests": 45,
    "estimated_affected": 562,
    "would_block": 45,
    "estimated_would_block": 562,
    "impact_percentage": 0.45,
    "sample_matches": [
      {
        "method": "GET",
        "path": "/admin/users",
        "client_ip": "203.0.113.45",
        "current_action": "allow"
      },
      ...
    ],
    "timestamp": "2025-11-14T14:00:00Z"
  }
}
```

### Interpret Results

- **affected_requests**: Number of requests that matched the condition
- **estimated_affected**: Extrapolated to full dataset (if sampled)
- **impact_percentage**: Percentage of total traffic affected
- **sample_matches**: First 10 matching requests for review

**Decision Matrix:**

| Impact % | Recommendation |
|----------|----------------|
| < 0.1%   | Low impact - safe to enforce |
| 0.1% - 1% | Medium impact - review samples carefully |
| 1% - 5%  | High impact - review thoroughly, may need adjustment |
| > 5%     | Very high impact - likely too broad, refine condition |

---

## Deploying to Production

### Switch to Enforce Mode

After validating in observe mode and reviewing simulation:

```bash
curl -X PATCH http://localhost:8000/v1/policy/policies/{policy_id}/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode": "enforce"}' | jq
```

**Result:** Policy now actively blocks matching requests.

### Monitor Impact

**Check Detection Events:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/v1/detection/detections/?detector_type=policy&status=open" | jq
```

**Check Dashboard:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/v1/dashboard/summary/" | jq '.detections'
```

### Rollback if Needed

**Disable Immediately:**
```bash
curl -X POST http://localhost:8000/v1/policy/policies/{policy_id}/disable/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Or Switch Back to Observe:**
```bash
curl -X PATCH http://localhost:8000/v1/policy/policies/{policy_id}/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"mode": "observe"}' | jq
```

---

## Common Policy Patterns

### 1. IP Allowlist/Blocklist

**Allow Only Corporate IPs:**
```json
{
  "condition": {
    "not": {
      "field": "client_ip",
      "op": "in_cidr",
      "value": "10.0.0.0/8"
    }
  },
  "action": {"type": "block"}
}
```

**Block Specific CIDR Range:**
```json
{
  "condition": {
    "field": "client_ip",
    "op": "in_cidr",
    "value": "192.0.2.0/24"
  },
  "action": {"type": "block"}
}
```

### 2. Path-Based Access Control

**Block All /admin Paths:**
```json
{
  "condition": {
    "field": "path",
    "op": "startswith",
    "value": "/admin"
  },
  "action": {"type": "block"}
}
```

**Allow Only Specific Endpoints:**
```json
{
  "condition": {
    "field": "path_pattern",
    "op": "not_in",
    "value": ["/api/v1/public", "/health", "/docs"]
  },
  "action": {"type": "block"}
}
```

### 3. Method-Based Restrictions

**Block All DELETE Requests:**
```json
{
  "condition": {
    "field": "method",
    "op": "eq",
    "value": "DELETE"
  },
  "action": {"type": "block"}
}
```

**Allow Only Read Methods:**
```json
{
  "condition": {
    "field": "method",
    "op": "not_in",
    "value": ["GET", "HEAD", "OPTIONS"]
  },
  "action": {"type": "block"}
}
```

### 4. Attack Pattern Detection

**SQL Injection Patterns:**
```json
{
  "condition": {
    "field": "path",
    "op": "regex",
    "value": ".*(union|select|drop|insert|update|delete|from|where).*"
  },
  "action": {"type": "block"}
}
```

**XSS Patterns:**
```json
{
  "condition": {
    "field": "path",
    "op": "regex",
    "value": ".*(script|onerror|onload|javascript:).*"
  },
  "action": {"type": "block"}
}
```

### 5. User-Agent Based Rules

**Block Known Bots:**
```json
{
  "condition": {
    "field": "request_meta.headers.user_agent",
    "op": "regex",
    "value": ".*(bot|crawler|scraper|spider).*"
  },
  "action": {"type": "challenge", "challenge_type": "captcha"}
}
```

**Require Modern Browsers:**
```json
{
  "condition": {
    "and": [
      {"field": "request_meta.headers.user_agent", "op": "regex", "value": ".*(MSIE|Trident).*"},
      {"field": "path", "op": "startswith", "value": "/app"}
    ]
  },
  "action": {"type": "block", "message": "Please use a modern browser"}
}
```

### 6. Rate Limiting by Path

**Throttle Payment Endpoints:**
```json
{
  "condition": {
    "field": "path_pattern",
    "op": "in",
    "value": ["/payments/charge", "/payments/refund"]
  },
  "action": {"type": "throttle", "response_code": 429}
}
```

### 7. Composite Rules

**Block External POST to Admin:**
```json
{
  "condition": {
    "and": [
      {"field": "method", "op": "eq", "value": "POST"},
      {"field": "path", "op": "startswith", "value": "/admin"},
      {
        "not": {
          "field": "client_ip",
          "op": "in_cidr",
          "value": "10.0.0.0/8"
        }
      }
    ]
  },
  "action": {"type": "block"}
}
```

---

## Troubleshooting

### Policy Not Matching Expected Requests

**Check:**
1. Policy is **enabled**: `is_enabled: true`
2. Policy is in **enforce** mode (if expecting blocks)
3. Field names are correct (check available fields in API_GUIDE.md)
4. Operators are correct (e.g., `in_cidr` for IPs, not `in`)
5. Values match exactly (case-sensitive unless using `contains`)

**Debug with Test Endpoint:**
```bash
curl -X POST http://localhost:8000/v1/policy/test/ \
  -H "Content-Type: application/json" \
  -d '{
    "condition": {...your condition...},
    "events": [{...sample event that should match...}]
  }' | jq
```

### Policy Blocking Too Much

**Steps:**
1. **Disable immediately:**
   ```bash
   curl -X POST .../policies/{id}/disable/ ...
   ```

2. **Review simulation results** - check `sample_matches`

3. **Refine condition** - make it more specific:
   ```json
   {
     "and": [
       {"field": "path", "op": "startswith", "value": "/admin"},
       {"field": "path", "op": "not_in", "value": ["/admin/health", "/admin/status"]}
     ]
   }
   ```

4. **Test again** with `/v1/policy/test/`

5. **Re-enable** in observe mode first

### Policy Not Visible in List

**Check filters:**
```bash
# List all policies (no filters)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/v1/policy/policies/" | jq

# Filter by app
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/v1/policy/policies/?app_id={app_id}" | jq

# Filter by enabled
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/v1/policy/policies/?is_enabled=true" | jq
```

### Cache Not Updating

Policies are cached for 5 minutes. After updates, cache is automatically invalidated, but if you see stale data:

**Wait 5 minutes** or **restart control plane:**
```bash
docker compose restart control-plane
```

### Simulation Returns No Data

**Possible causes:**
1. No historical events in database (run `generate_test_detections` to create events)
2. Date range too narrow (increase `days` parameter)
3. App has no traffic (check different app_id)

**Solution:**
```bash
# Generate test events first
docker compose exec control-plane python manage.py generate_test_detections --count=100

# Then run simulation
curl -X POST .../simulate/ -d '{"days": 14}' ...
```

---

## Command Reference

### Management Commands

```bash
# Create example policies
python manage.py create_example_policies

# Create example policies for specific org/app
python manage.py create_example_policies --org-slug=acme-corp --app-slug=payment-api

# Clear existing examples first
python manage.py create_example_policies --clear

# Generate test events (for simulation testing)
python manage.py generate_test_detections --count=100
```

### API Endpoints

```
GET    /v1/policy/policies/                  List policies
POST   /v1/policy/policies/                  Create policy
GET    /v1/policy/policies/{id}/             Get policy
PATCH  /v1/policy/policies/{id}/             Update policy
DELETE /v1/policy/policies/{id}/             Delete policy
POST   /v1/policy/policies/{id}/enable/      Enable policy
POST   /v1/policy/policies/{id}/disable/     Disable policy
POST   /v1/policy/policies/{id}/simulate/    Run simulation
POST   /v1/policy/test/                      Test DSL
```

---

## Next Steps

1. **Create your first policy** following the workflow above
2. **Review example policies** in Django admin or via API
3. **Test with sample events** using `/v1/policy/test/`
4. **Run simulations** before deploying to production
5. **Monitor impact** after enabling enforcement

For complete API reference, see **API_GUIDE.md** - Phase 6: Policy Engine section.

For implementation details, see **IMPLEMENTATION_BLUEPRINT.md** - Part 3: Phase 6.

---

**Happy Policy Building! 🛡️**
