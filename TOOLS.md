# Sentrix - Tools & Management Commands

Complete reference for all management commands, utilities, and developer tools.

---

## Table of Contents

1. [Management Commands](#management-commands)
2. [API Testing Tools](#api-testing-tools)
3. [Database Tools](#database-tools)
4. [Monitoring Tools](#monitoring-tools)
5. [Development Utilities](#development-utilities)

---

## Management Commands

All commands should be run inside the control-plane container:

```bash
docker compose exec control-plane python manage.py <command>
```

---

### Core Data Management

#### `create_test_data`

Creates test data for development (org, subscription, users, apps).

**Usage:**
```bash
python manage.py create_test_data
```

**Creates:**
- 1 Organization (Acme Corporation)
- 1 Subscription (Pro plan)
- 3 Users (admin, analyst, viewer)
- 2 Applications (Payment API, Logistics API)

**Output:**
```
Creating test data...
✓ Created organization: Acme Corporation (uuid)
✓ Created subscription: pro (uuid)
✓ Created admin user: admin@acme.com (password: admin123)
✓ Created analyst user: analyst@acme.com (password: analyst123)
✓ Created viewer user: viewer@acme.com (password: viewer123)
✓ Created application: Payment API (uuid)
✓ Created application: Logistics API (uuid)
```

**Credentials:**
- Admin: `admin@acme.com` / `admin123`
- Analyst: `analyst@acme.com` / `analyst123`
- Viewer: `viewer@acme.com` / `viewer123`

**Idempotent:** Can be run multiple times (uses get_or_create)

---

### Detection Tools

#### `generate_test_detections`

Generates test detection events for testing the detection pipeline.

**Usage:**
```bash
# Generate 20 test detections (default)
python manage.py generate_test_detections

# Generate 100 test detections
python manage.py generate_test_detections --count=100
```

**Options:**
- `--count <N>` - Number of test events to generate (default: 20)

**Creates:**
- Events with SQL injection patterns
- Events with XSS patterns
- Events with suspicious path access
- Publishes to `enriched.events` Kafka topic
- Detector consumer processes and creates DetectionEvent records

**Output:**
```
Generating 20 test detection events...
Using org: Acme Corporation, app: Payment API

  1. Published sqli event: /api/users
  2. Published sqli event: /api/products
  3. Published xss event: /api/comments
  ...

✓ Generated 20 test events

Events published to Kafka topic: enriched.events
The detector consumer will process them and create detections.
```

**Use Cases:**
- Test detection pipeline
- Populate dashboard with sample data
- Verify detector consumer is working
- Test detection APIs

---

### Policy Tools

#### `create_example_policies`

Creates 8 production-ready example policies for testing and demonstration.

**Usage:**
```bash
# Create examples for first org/app (default)
python manage.py create_example_policies

# Create for specific org
python manage.py create_example_policies --org-slug=acme-corp

# Create for specific org and app
python manage.py create_example_policies --org-slug=acme-corp --app-slug=payment-api

# Clear existing examples first
python manage.py create_example_policies --clear
```

**Options:**
- `--org-slug <slug>` - Organization slug (default: first org)
- `--app-slug <slug>` - Application slug (default: first app)
- `--clear` - Delete existing example policies before creating

**Creates 8 Policies:**
1. Block External Admin Access (priority: 10)
2. Throttle Payment Endpoints (priority: 50)
3. Block SQL Injection Attempts (priority: 1)
4. Challenge Bot Traffic (priority: 100)
5. Block Sensitive Path Access (priority: 5)
6. Country-Based Blocking (org-level, priority: 5)
7. Require Content-Type for POST (priority: 20)
8. Enforce Allowed HTTP Methods (priority: 15)

**Output:**
```
Creating example policies for org: Acme Corporation
Application: Payment API

  ✓ Created: Block External Admin Access (app: Payment API) - mode=observe, enabled=False, priority=10
  ✓ Created: Throttle Payment Endpoints (app: Payment API) - mode=observe, enabled=False, priority=50
  ...

Created 8 example policies

Note: All policies are created in OBSERVE mode and DISABLED
To enable a policy:
  1. Review the policy in Django admin or via API
  2. Test with /v1/policy/test/ endpoint
  3. Run simulation: POST /v1/policy/policies/{id}/simulate/
  4. Enable: POST /v1/policy/policies/{id}/enable/
  5. Switch to enforce mode: PATCH /v1/policy/policies/{id}/ {"mode": "enforce"}
```

**Safety:**
- All policies start **disabled**
- All policies start in **observe mode**
- No automatic enforcement
- Safe for production testing

---

### Consumer Management

#### `run_enrichment_consumer`

Runs the enrichment Kafka consumer (consumes `ingest.events`, produces `enriched.events`).

**Usage:**
```bash
python manage.py run_enrichment_consumer
```

**Function:**
- Consumes raw events from `ingest.events`
- Enriches with GeoIP, User-Agent parsing, path canonicalization
- Discovers and catalogs API endpoints
- Produces to `enriched.events`

**Note:** Usually run via Docker Compose, not manually.

---

#### `run_detector_consumer`

Runs the detector Kafka consumer (consumes `enriched.events`, produces `detection.events`).

**Usage:**
```bash
python manage.py run_detector_consumer
```

**Function:**
- Consumes enriched events from `enriched.events`
- Runs pattern-based detectors (SQL injection, XSS, suspicious paths)
- Calls Deepseek-R1 for high-confidence events
- Creates DetectionEvent records
- Produces to `detection.events`

**Note:** Usually run via Docker Compose, not manually.

---

### Database Management

#### `migrate`

Applies database migrations.

**Usage:**
```bash
python manage.py migrate
```

**Standard Django command** - applies all pending migrations.

---

#### `makemigrations`

Creates new migration files based on model changes.

**Usage:**
```bash
python manage.py makemigrations
```

**Standard Django command** - generates migration files.

---

#### `createsuperuser`

Creates a Django admin superuser.

**Usage:**
```bash
python manage.py createsuperuser
```

**Interactive** - prompts for email and password.

**Use:** Access Django admin at http://localhost:8000/admin

---

### Utility Commands

#### `shell`

Opens Django shell with database access.

**Usage:**
```bash
python manage.py shell
```

**Examples:**
```python
# Query organizations
from core.models import Organization
orgs = Organization.objects.all()
for org in orgs:
    print(org.name, org.org_id)

# Query policies
from policy.models import Policy
policies = Policy.objects.filter(is_enabled=True)
for policy in policies:
    print(policy.name, policy.mode, policy.priority)

# Test policy evaluator
from policy.evaluator import PolicyEvaluator
evaluator = PolicyEvaluator()
event = {'method': 'POST', 'path': '/admin/users', 'client_ip': '192.168.1.100'}
condition = {'field': 'path', 'op': 'startswith', 'value': '/admin'}
result = evaluator.evaluate(condition, event)
print(result)  # True
```

---

#### `dbshell`

Opens PostgreSQL shell.

**Usage:**
```bash
python manage.py dbshell
```

**Direct SQL access:**
```sql
-- List tables
\dt

-- Count events
SELECT COUNT(*) FROM api_request_event;

-- Count detections by severity
SELECT severity, COUNT(*)
FROM detection_event
GROUP BY severity;

-- List policies
SELECT name, mode, is_enabled, priority
FROM policy
ORDER BY priority;
```

---

## API Testing Tools

### cURL Examples

All examples assume you have a token:

```bash
# Login and save token
curl -X POST http://localhost:8000/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@acme.com", "password": "admin123"}' \
  | jq -r '.access_token' > token.txt

export TOKEN=$(cat token.txt)
```

#### Test Policy DSL

```bash
curl -X POST http://localhost:8000/v1/policy/test/ \
  -H "Content-Type: application/json" \
  -d '{
    "condition": {
      "field": "path",
      "op": "startswith",
      "value": "/admin"
    },
    "events": [
      {"method": "GET", "path": "/admin/users"},
      {"method": "GET", "path": "/api/users"}
    ]
  }' | jq
```

#### List Policies

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/policy/policies/ | jq
```

#### Simulate Policy

```bash
curl -X POST http://localhost:8000/v1/policy/policies/{policy_id}/simulate/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"days": 7}' | jq
```

#### List Detections

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/detection/detections/ | jq
```

#### Dashboard Summary

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/dashboard/summary/ | jq
```

---

### Test Scripts

#### `test_policy_evaluator.py`

Standalone test for policy DSL evaluator (no Django required).

**Usage:**
```bash
cd /home/user/sentrix
python test_policy_evaluator.py
```

**Output:**
```
✓ Test 1: Simple equality
✓ Test 2: AND condition
✓ Test 3: OR condition
✓ Test 4: NOT condition
✓ Test 5: IP in CIDR
✓ Test 6: Nested field access
✓ Test 7: Complex nested condition

✅ All tests passed!
```

**Tests:**
- Simple field equality
- Logical operators (and/or/not)
- IP CIDR matching
- Nested field access
- Complex nested conditions

---

## Database Tools

### PostgreSQL Tools

**Connect to PostgreSQL:**
```bash
docker compose exec postgres psql -U sentrix -d sentrix
```

**Useful Queries:**

```sql
-- List all tables
\dt

-- Table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- List partitions
SELECT tablename
FROM pg_tables
WHERE tablename LIKE 'api_request_event_%';

-- Count events by date
SELECT
  DATE(timestamp) as date,
  COUNT(*) as count
FROM api_request_event
GROUP BY DATE(timestamp)
ORDER BY date DESC;

-- Top endpoints by request count
SELECT
  method,
  path_pattern,
  request_count,
  last_seen
FROM api_endpoint
ORDER BY request_count DESC
LIMIT 10;

-- Detections by severity
SELECT
  severity,
  COUNT(*) as count,
  AVG(confidence_score) as avg_confidence
FROM detection_event
GROUP BY severity
ORDER BY
  CASE severity
    WHEN 'critical' THEN 1
    WHEN 'high' THEN 2
    WHEN 'medium' THEN 3
    WHEN 'low' THEN 4
    WHEN 'info' THEN 5
  END;

-- Policies summary
SELECT
  name,
  mode,
  is_enabled,
  priority,
  is_org_level
FROM policy
ORDER BY priority, created_at DESC;
```

---

### Redis Tools

**Connect to Redis:**
```bash
docker compose exec redis redis-cli
```

**Useful Commands:**

```bash
# Check if Redis is running
PING

# List all keys
KEYS *

# Get policy cache
KEYS policies:*

# Get specific policy cache
GET policies:org:<org_id>:app:<app_id>

# Get decision cache
KEYS decision:*

# Get rate limit keys
KEYS ratelimit:*

# View TTL
TTL decision:<fingerprint>

# Clear all cache
FLUSHALL

# Clear policy cache only
KEYS policies:* | xargs redis-cli DEL

# Monitor commands in real-time
MONITOR
```

---

### Kafka Tools

**List topics:**
```bash
docker compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

**Describe topic:**
```bash
docker compose exec kafka kafka-topics --describe \
  --topic enriched.events \
  --bootstrap-server localhost:9092
```

**Consume messages:**
```bash
# Latest messages
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic enriched.events \
  --from-beginning \
  --max-messages 10

# Tail messages
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic enriched.events
```

**Check consumer groups:**
```bash
docker compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --list

# Describe group
docker compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group enrichment-group \
  --describe
```

**Create topic:**
```bash
docker compose exec kafka kafka-topics \
  --create \
  --topic test.events \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1
```

---

## Monitoring Tools

### Health Checks

**Application Health:**
```bash
curl http://localhost:8000/health/
```

**Expected Response:**
```json
{"status": "healthy"}
```

**Model Server Health:**
```bash
curl http://localhost:8001/health
```

**Expected Response:**
```json
{"status": "healthy", "model": "r1-stub-v1"}
```

---

### Log Viewing

**Control Plane:**
```bash
docker compose logs -f control-plane
```

**Enrichment Consumer:**
```bash
docker compose logs -f enrichment-consumer
```

**Detector Consumer:**
```bash
docker compose logs -f detector-consumer
```

**All Services:**
```bash
docker compose logs -f
```

**Filter Logs:**
```bash
# Errors only
docker compose logs control-plane | grep ERROR

# Policy-related
docker compose logs control-plane | grep -i policy

# Detection-related
docker compose logs detector-consumer | grep -i detection
```

---

### Service Status

**Check all services:**
```bash
docker compose ps
```

**Restart service:**
```bash
docker compose restart control-plane
docker compose restart enrichment-consumer
docker compose restart detector-consumer
```

**View resource usage:**
```bash
docker compose top
docker stats
```

---

## Development Utilities

### Code Formatting

**Black (Python formatter):**
```bash
black backend/
```

**isort (Import sorter):**
```bash
isort backend/
```

**flake8 (Linter):**
```bash
flake8 backend/
```

---

### Testing

**Run Python tests:**
```bash
# Policy evaluator tests
python test_policy_evaluator.py

# Django tests (when available)
docker compose exec control-plane python manage.py test
```

---

### Quick Reset

**Reset entire stack:**
```bash
# Stop all services
docker compose down

# Remove volumes (WARNING: deletes all data)
docker compose down -v

# Rebuild and start
docker compose up -d --build

# Recreate test data
docker compose exec control-plane python manage.py migrate
docker compose exec control-plane python manage.py create_test_data
docker compose exec control-plane python manage.py create_example_policies
docker compose exec control-plane python manage.py generate_test_detections --count=50
```

---

## Summary

### Essential Commands

```bash
# Start stack
docker compose up -d

# Create test data
docker compose exec control-plane python manage.py create_test_data

# Create policies
docker compose exec control-plane python manage.py create_example_policies

# Generate detections
docker compose exec control-plane python manage.py generate_test_detections --count=50

# View logs
docker compose logs -f control-plane

# Check status
docker compose ps

# Access Django admin
open http://localhost:8000/admin
```

### Test Credentials

- **Admin:** admin@acme.com / admin123
- **Analyst:** analyst@acme.com / analyst123
- **Viewer:** viewer@acme.com / viewer123

### Important URLs

- **API Base:** http://localhost:8000/v1/
- **Django Admin:** http://localhost:8000/admin/
- **Health Check:** http://localhost:8000/health/
- **Model Server:** http://localhost:8001/

---

For complete API documentation, see **API_GUIDE.md**.

For policy usage guide, see **POLICY_GUIDE.md**.

For implementation details, see **IMPLEMENTATION_BLUEPRINT.md**.
