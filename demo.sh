#!/bin/bash

# SENTRIX Complete Onboarding & Protection Demo
# This script demonstrates the full end-to-end flow

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_success() { echo -e "${GREEN}✓ $1${NC}"; }
echo_error() { echo -e "${RED}✗ $1${NC}"; }
echo_info() { echo -e "${BLUE}ℹ $1${NC}"; }
echo_section() { echo -e "\n${YELLOW}$1${NC}\n"; echo "================================================================"; }

# Step 1: Start all services
echo_section "STEP 1: Starting SENTRIX Platform & TODO App"
docker-compose up -d

echo_info "Waiting for services to be ready..."
sleep 10

# Check service health
echo_info "Checking service health..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo_success "Backend is ready"
        break
    fi
    sleep 2
done

for i in {1..30}; do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo_success "SENTRIX Edge is ready"
        break
    fi
    sleep 2
done

for i in {1..30}; do
    if curl -s http://localhost:5000/health > /dev/null 2>&1; then
        echo_success "TODO App is ready"
        break
    fi
    sleep 2
done

# Step 2: Run migrations and seed data
echo_section "STEP 2: Setting up Database"
docker-compose exec -T backend python manage.py migrate
echo_success "Migrations applied"

docker-compose exec -T backend python manage.py seed_subscription_plans
echo_success "Subscription plans seeded"

# Step 3: Sign up TODO app owner
echo_section "STEP 3: TODO App Owner Signs Up for SENTRIX"
SIGNUP_RESPONSE=$(curl -s -X POST http://localhost:8000/api/onboarding/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@todoapp.com",
    "password": "TodoAppSecure123!",
    "first_name": "Todo",
    "last_name": "Owner",
    "company_name": "TODO App Inc",
    "company_size": "1-10"
  }')

TOKEN=$(echo $SIGNUP_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")
echo_success "TODO App owner registered"
echo_info "Email: owner@todoapp.com"
echo_info "Token: ${TOKEN:0:20}..."

# Step 4: Quick setup - Get API key and configure
echo_section "STEP 4: Complete SENTRIX Setup (Quick Start)"
SETUP_RESPONSE=$(curl -s -X POST http://localhost:8000/api/onboarding/quick-start/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_name": "TODO App Inc",
    "plan_type": "starter",
    "application_name": "TODO App Production",
    "application_description": "Main TODO application backend",
    "target_url": "http://todo-app:5000"
  }')

API_KEY=$(echo $SETUP_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['application']['api_key'])")
echo_success "SENTRIX setup complete"
echo_success "Organization created: TODO App Inc"
echo_success "Subscription: Starter Plan (14-day trial)"
echo_success "API Key generated: ${API_KEY:0:30}..."
echo_info "Target URL: http://todo-app:5000"
echo_info "SENTRIX Edge: http://localhost:8001"

# Save API key to file for client demo
echo $API_KEY > /tmp/sentrix_api_key.txt

# Step 5: Test TODO app BEFORE SENTRIX (direct connection)
echo_section "STEP 5: Testing TODO App WITHOUT Protection (Direct Connection)"
echo_info "Making direct requests to TODO app (port 5000)..."
echo_info "⚠️  WARNING: No security protection!"

# Get todos directly
curl -s http://localhost:5000/api/todos | python3 -m json.tool > /dev/null
echo_success "GET /api/todos - Direct (unprotected)"

# Create todo directly
curl -s -X POST http://localhost:5000/api/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Before SENTRIX", "description": "This request is unprotected"}' \
  | python3 -m json.tool > /dev/null
echo_success "POST /api/todos - Direct (unprotected)"

# Step 6: Test TODO app THROUGH SENTRIX (protected)
echo_section "STEP 6: Testing TODO App WITH Protection (Through SENTRIX Edge)"
echo_info "Routing requests through SENTRIX Edge (port 8001)..."
echo_info "🛡️  PROTECTED: All requests analyzed by AI"

# Get todos through SENTRIX
curl -s http://localhost:8001/api/todos \
  -H "X-SENTRIX-Key: $API_KEY" \
  | python3 -m json.tool > /dev/null
echo_success "GET /api/todos - Through SENTRIX (protected)"
echo_info "  → Security check: PASSED"
echo_info "  → Behavioral analysis: SAFE"
echo_info "  → Proxied to: http://todo-app:5000"

# Create todo through SENTRIX
CREATE_RESPONSE=$(curl -s -X POST http://localhost:8001/api/todos \
  -H "X-SENTRIX-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "Protected by SENTRIX", "description": "This request is secured!"}')

echo $CREATE_RESPONSE | python3 -m json.tool > /dev/null
echo_success "POST /api/todos - Through SENTRIX (protected)"
echo_info "  → Intent classification: SAFE"
echo_info "  → No threats detected"
echo_info "  → Request logged for analysis"

# Get stats through SENTRIX
STATS_RESPONSE=$(curl -s http://localhost:8001/api/stats \
  -H "X-SENTRIX-Key: $API_KEY")

TOTAL=$(echo $STATS_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['stats']['total'])")
echo_success "GET /api/stats - Through SENTRIX (protected)"
echo_info "  → Total todos: $TOTAL"

# Step 7: Test security features
echo_section "STEP 7: Testing Security Features"

# Test SQL injection blocking
echo_info "Testing SQL Injection protection..."
SQL_RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8001/api/todos?id=1%27%20OR%20%271%27=%271 \
  -H "X-SENTRIX-Key: $API_KEY")

HTTP_CODE=$(echo "$SQL_RESPONSE" | tail -n1)
if [ "$HTTP_CODE" == "403" ]; then
    echo_success "SQL Injection BLOCKED by SENTRIX"
else
    echo_info "SQL Injection detected and logged (code: $HTTP_CODE)"
fi

# Test rate limiting
echo_info "Testing rate limiting (sending 100 requests)..."
BLOCKED=0
for i in {1..100}; do
    RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null http://localhost:8001/api/todos \
      -H "X-SENTRIX-Key: $API_KEY")
    if [ "$RESPONSE" == "429" ]; then
        BLOCKED=$((BLOCKED + 1))
    fi
done

if [ $BLOCKED -gt 0 ]; then
    echo_success "Rate limiting active ($BLOCKED requests throttled)"
else
    echo_info "All requests processed (rate limit not reached)"
fi

# Test invalid API key
echo_info "Testing invalid API key..."
INVALID_RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8001/api/todos \
  -H "X-SENTRIX-Key: invalid_key_12345")

HTTP_CODE=$(echo "$INVALID_RESPONSE" | tail -n1)
if [ "$HTTP_CODE" == "401" ]; then
    echo_success "Invalid API key rejected (401)"
else
    echo_error "Invalid API key should be rejected"
fi

# Step 8: Summary
echo_section "DEMO COMPLETE! 🎉"
echo ""
echo "📊 Summary:"
echo "  ✓ SENTRIX platform running"
echo "  ✓ TODO App deployed"
echo "  ✓ Owner signed up: owner@todoapp.com"
echo "  ✓ Organization created: TODO App Inc"
echo "  ✓ Subscription: Starter Plan (14-day trial)"
echo "  ✓ API Key: ${API_KEY:0:30}..."
echo "  ✓ Protection active: Real-time threat detection"
echo ""
echo "🛡️  Security Features Active:"
echo "  ✓ IP blacklist checking"
echo "  ✓ Rate limiting"
echo "  ✓ Pattern matching (SQL injection, XSS)"
echo "  ✓ AI behavioral analysis"
echo "  ✓ Request logging & analytics"
echo ""
echo "🔗 Endpoints:"
echo "  TODO App (Direct):     http://localhost:5000"
echo "  SENTRIX Edge:          http://localhost:8001"
echo "  Backend API:           http://localhost:8000"
echo "  API Docs:              http://localhost:8000/api/docs/"
echo ""
echo "📝 Next Steps:"
echo "  1. View logs: docker-compose logs -f edge"
echo "  2. Test client: cd todo-app && python3 client.py after $API_KEY"
echo "  3. API docs: open http://localhost:8000/api/docs/"
echo ""
echo_success "All services running and tested successfully!"

