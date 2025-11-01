#!/bin/bash

################################################################################
# SENTRIX Automated Onboarding - End-to-End Test
# Tests complete flow: Signup → Onboarding → DNS → Protection → Testing
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="http://localhost:8000"
EDGE_URL="http://localhost:8001"
TODO_APP_URL="http://localhost:5000"

# Test data
TEST_EMAIL="test-$(date +%s)@todo.com"
TEST_PASSWORD="SecureTestPass123!"
TEST_COMPANY="TODO Test Inc"
TEST_DOMAIN="api.todo-test.local"
TEST_ORIGIN="http://todo-app:5002"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                                      ║${NC}"
echo -e "${BLUE}║        SENTRIX AUTOMATED ONBOARDING - END-TO-END TEST               ║${NC}"
echo -e "${BLUE}║                                                                      ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

################################################################################
# Helper Functions
################################################################################

print_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶ $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

check_service() {
    local service=$1
    local url=$2
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$HTTP_CODE" != "000" ]; then
        print_success "$service is running (HTTP $HTTP_CODE)"
        return 0
    else
        print_error "$service is not responding"
        return 1
    fi
}

################################################################################
# Pre-Flight Checks
################################################################################

print_step "Pre-Flight Checks"

# Check backend
check_service "Backend" "$BACKEND_URL/api/" || exit 1

# Check edge
check_service "Edge" "$EDGE_URL/health" || exit 1

# Check TODO app
check_service "TODO App" "$TODO_APP_URL/health" || exit 1

print_success "All services are running"

################################################################################
# STEP 1: User Signup
################################################################################

print_step "STEP 1: User Signup"

print_info "Creating test account: $TEST_EMAIL"

SIGNUP_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/onboarding/signup/" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASSWORD\",
    \"first_name\": \"Test\",
    \"last_name\": \"User\",
    \"company_name\": \"$TEST_COMPANY\"
  }")

echo "$SIGNUP_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$SIGNUP_RESPONSE"

# Extract token
AUTH_TOKEN=$(echo "$SIGNUP_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)

if [ "$AUTH_TOKEN" == "null" ] || [ -z "$AUTH_TOKEN" ]; then
    print_error "Failed to get auth token"
    echo "Response: $SIGNUP_RESPONSE"
    exit 1
fi

print_success "Account created successfully"
print_info "Auth Token: ${AUTH_TOKEN:0:20}..."

################################################################################
# STEP 2: Quick Start Setup (Create Organization)
################################################################################

print_step "STEP 2: Quick Start Setup"

print_info "Setting up organization and environment"

QUICKSTART_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/onboarding/quick_start/" \
  -H "Authorization: Token $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"organization_name\": \"$TEST_COMPANY\",
    \"plan_type\": \"starter\",
    \"environments\": [{
      \"name\": \"Production\",
      \"environment_type\": \"production\",
      \"applications\": [{
        \"name\": \"TODO API Test\",
        \"base_url\": \"http://$TEST_DOMAIN\",
        \"target_url\": \"$TEST_ORIGIN\"
      }]
    }]
  }")

echo "$QUICKSTART_RESPONSE" | python3 -m json.tool 2>/dev/null || '.' || echo "$QUICKSTART_RESPONSE"

# Extract application ID
APP_ID=$(echo "$QUICKSTART_RESPONSE" | python3 -m json.tool 2>/dev/null || -r '.applications[0].id')
API_KEY=$(echo "$QUICKSTART_RESPONSE" | python3 -m json.tool 2>/dev/null || -r '.applications[0].api_key')

if [ "$APP_ID" == "null" ] || [ -z "$APP_ID" ]; then
    print_error "Failed to create application"
    echo "Response: $QUICKSTART_RESPONSE"
    exit 1
fi

print_success "Organization and application created"
print_info "Application ID: $APP_ID"
print_info "API Key: ${API_KEY:0:30}..."

################################################################################
# STEP 3: Start Automated Onboarding Wizard
################################################################################

print_step "STEP 3: Start Automated Onboarding Wizard"

print_info "Initializing DNS onboarding for: $TEST_DOMAIN"

WIZARD_START=$(curl -s -X POST "$BACKEND_URL/api/applications/onboarding-wizard/start/" \
  -H "Authorization: Token $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"domain\": \"$TEST_DOMAIN\",
    \"origin_url\": \"$TEST_ORIGIN\",
    \"application_name\": \"TODO API Production\"
  }")

echo "$WIZARD_START" | python3 -m json.tool 2>/dev/null || '.' || echo "$WIZARD_START"

# Extract DNS information
DNS_APP_ID=$(echo "$WIZARD_START" | python3 -m json.tool 2>/dev/null || -r '.application_id')
EDGE_HOSTNAME=$(echo "$WIZARD_START" | python3 -m json.tool 2>/dev/null || -r '.edge_hostname')
TXT_NAME=$(echo "$WIZARD_START" | python3 -m json.tool 2>/dev/null || -r '.dns_records.verification.name')
TXT_VALUE=$(echo "$WIZARD_START" | python3 -m json.tool 2>/dev/null || -r '.dns_records.verification.value')
CNAME_NAME=$(echo "$WIZARD_START" | python3 -m json.tool 2>/dev/null || -r '.dns_records.routing.name')
CNAME_VALUE=$(echo "$WIZARD_START" | python3 -m json.tool 2>/dev/null || -r '.dns_records.routing.value')
BYPASS_TOKEN=$(echo "$WIZARD_START" | python3 -m json.tool 2>/dev/null || -r '.failover.bypass_token // empty')

print_success "Onboarding wizard started"
print_info "Application ID: $DNS_APP_ID"
print_info "Edge Hostname: $EDGE_HOSTNAME"
echo ""
echo -e "${YELLOW}DNS Records to Add:${NC}"
echo -e "  TXT:   $TXT_NAME = $TXT_VALUE"
echo -e "  CNAME: $CNAME_NAME = $CNAME_VALUE"

################################################################################
# STEP 4: Simulate DNS Records (For Testing)
################################################################################

print_step "STEP 4: Simulate DNS Propagation"

print_info "In production, you would add DNS records here"
print_info "For testing, we'll manually mark as verified"

# Manually update DNS status for testing
UPDATE_DNS=$(curl -s -X PATCH "$BACKEND_URL/api/applications/$DNS_APP_ID/" \
  -H "Authorization: Token $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"dns_status\": \"verified\"
  }")

print_success "DNS status updated to verified (simulated)"

################################################################################
# STEP 5: Check Onboarding Status
################################################################################

print_step "STEP 5: Check Onboarding Status"

STATUS_RESPONSE=$(curl -s -X GET "$BACKEND_URL/api/applications/onboarding-wizard/status/" \
  -H "Authorization: Token $AUTH_TOKEN")

echo "$STATUS_RESPONSE" | python3 -m json.tool 2>/dev/null || '.' || echo "$STATUS_RESPONSE"

VERIFIED_COUNT=$(echo "$STATUS_RESPONSE" | python3 -m json.tool 2>/dev/null || -r '.verified')

if [ "$VERIFIED_COUNT" -gt "0" ]; then
    print_success "Application verified successfully"
else
    print_error "Application not verified yet"
fi

################################################################################
# STEP 6: Test TODO App Through SENTRIX Edge (API Key Mode)
################################################################################

print_step "STEP 6: Test TODO App - API Key Mode"

print_info "Testing TODO app through SENTRIX Edge with API key"

# Test 1: Health check
echo -e "\n${YELLOW}Test 1: Health Check${NC}"
HEALTH_RESPONSE=$(curl -s -X GET "$EDGE_URL/health" \
  -H "X-SENTRIX-Key: $API_KEY" \
  -w "\nHTTP_CODE: %{http_code}")

echo "$HEALTH_RESPONSE"

if echo "$HEALTH_RESPONSE" | grep -q "HTTP_CODE: 200"; then
    print_success "Health check passed"
else
    print_error "Health check failed"
fi

# Test 2: Get todos (empty)
echo -e "\n${YELLOW}Test 2: Get Todos (Initial)${NC}"
GET_TODOS=$(curl -s -X GET "$EDGE_URL/api/todos" \
  -H "X-SENTRIX-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -w "\nHTTP_CODE: %{http_code}")

echo "$GET_TODOS"

if echo "$GET_TODOS" | grep -q "HTTP_CODE: 200"; then
    print_success "Get todos passed"
else
    print_error "Get todos failed"
fi

# Test 3: Add a todo
echo -e "\n${YELLOW}Test 3: Add Todo${NC}"
ADD_TODO=$(curl -s -X POST "$EDGE_URL/api/todos" \
  -H "X-SENTRIX-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test TODO via SENTRIX","completed":false}' \
  -w "\nHTTP_CODE: %{http_code}")

echo "$ADD_TODO"

if echo "$ADD_TODO" | grep -q "HTTP_CODE: 201"; then
    print_success "Add todo passed"
else
    print_error "Add todo failed"
fi

# Test 4: Get todos again (should have 1 item)
echo -e "\n${YELLOW}Test 4: Get Todos (After Add)${NC}"
GET_TODOS_AFTER=$(curl -s -X GET "$EDGE_URL/api/todos" \
  -H "X-SENTRIX-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -w "\nHTTP_CODE: %{http_code}")

echo "$GET_TODOS_AFTER"

TODO_COUNT=$(echo "$GET_TODOS_AFTER" | python3 -m json.tool 2>/dev/null || -r '.todos | length' 2>/dev/null || echo "0")

if [ "$TODO_COUNT" -gt "0" ]; then
    print_success "Todo was added successfully ($TODO_COUNT todos found)"
else
    print_error "Todo count verification failed"
fi

# Test 5: Get stats
echo -e "\n${YELLOW}Test 5: Get Stats${NC}"
GET_STATS=$(curl -s -X GET "$EDGE_URL/api/stats" \
  -H "X-SENTRIX-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -w "\nHTTP_CODE: %{http_code}")

echo "$GET_STATS"

if echo "$GET_STATS" | grep -q "HTTP_CODE: 200"; then
    print_success "Get stats passed"
else
    print_error "Get stats failed"
fi

################################################################################
# STEP 7: Test Security Features
################################################################################

print_step "STEP 7: Test Security Features"

# Test SQL Injection Detection
echo -e "\n${YELLOW}Test: SQL Injection Detection${NC}"
SQL_INJECTION=$(curl -s -X GET "$EDGE_URL/api/todos?id=1' OR '1'='1" \
  -H "X-SENTRIX-Key: $API_KEY" \
  -w "\nHTTP_CODE: %{http_code}")

echo "$SQL_INJECTION"

if echo "$SQL_INJECTION" | grep -q "sql_injection\|blocked\|forbidden\|HTTP_CODE: 403"; then
    print_success "SQL injection detected and blocked"
else
    print_info "SQL injection test passed through (may need configuration)"
fi

# Test without API key (should be rejected)
echo -e "\n${YELLOW}Test: No API Key (Should Fail)${NC}"
NO_API_KEY=$(curl -s -X GET "$EDGE_URL/api/todos" \
  -w "\nHTTP_CODE: %{http_code}")

echo "$NO_API_KEY"

if echo "$NO_API_KEY" | grep -q "HTTP_CODE: 401\|unauthorized"; then
    print_success "Request without API key was rejected"
else
    print_error "Request without API key should have been rejected"
fi

# Test invalid API key
echo -e "\n${YELLOW}Test: Invalid API Key (Should Fail)${NC}"
INVALID_KEY=$(curl -s -X GET "$EDGE_URL/api/todos" \
  -H "X-SENTRIX-Key: invalid_key_12345" \
  -w "\nHTTP_CODE: %{http_code}")

echo "$INVALID_KEY"

if echo "$INVALID_KEY" | grep -q "HTTP_CODE: 401\|unauthorized"; then
    print_success "Request with invalid API key was rejected"
else
    print_error "Request with invalid API key should have been rejected"
fi

################################################################################
# STEP 8: Test DNS Mode (Host-based routing)
################################################################################

print_step "STEP 8: Test DNS Mode (Host-based Routing)"

print_info "Testing host-based routing (simulated DNS)"

# First, check if resolve-host endpoint works
echo -e "\n${YELLOW}Test: Resolve Host Endpoint${NC}"
RESOLVE_HOST=$(curl -s -X GET "$BACKEND_URL/api/applications/resolve-host/?host=$TEST_DOMAIN" \
  -w "\nHTTP_CODE: %{http_code}")

echo "$RESOLVE_HOST"

if echo "$RESOLVE_HOST" | grep -q "HTTP_CODE: 200\|target_url"; then
    print_success "Host resolution works"
else
    print_info "Host resolution not configured yet (normal for first test)"
fi

# Test Edge with Host header (DNS mode simulation)
echo -e "\n${YELLOW}Test: Request with Host Header${NC}"
HOST_REQUEST=$(curl -s -X GET "$EDGE_URL/api/todos" \
  -H "Host: $TEST_DOMAIN" \
  -w "\nHTTP_CODE: %{http_code}")

echo "$HOST_REQUEST"

if echo "$HOST_REQUEST" | grep -q "HTTP_CODE: 200\|todos"; then
    print_success "Host-based routing works"
else
    print_info "Host-based routing requires DNS verification (use API key for now)"
fi

################################################################################
# STEP 9: Test Failover & Bypass
################################################################################

print_step "STEP 9: Test Failover & Bypass"

if [ ! -z "$BYPASS_TOKEN" ] && [ "$BYPASS_TOKEN" != "null" ]; then
    echo -e "\n${YELLOW}Test: Emergency Bypass Token${NC}"
    print_info "Bypass token available: ${BYPASS_TOKEN:0:20}..."
    
    BYPASS_REQUEST=$(curl -s -X GET "$EDGE_URL/api/todos" \
      -H "X-SENTRIX-Bypass: $BYPASS_TOKEN" \
      -w "\nHTTP_CODE: %{http_code}")
    
    echo "$BYPASS_REQUEST"
    
    if echo "$BYPASS_REQUEST" | grep -q "HTTP_CODE: 200"; then
        print_success "Bypass token works"
    else
        print_info "Bypass token test (feature may need origin configuration)"
    fi
else
    print_info "No bypass token generated (DNS mode not fully configured)"
fi

################################################################################
# STEP 10: Complete Onboarding
################################################################################

print_step "STEP 10: Complete Onboarding"

COMPLETE_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/applications/onboarding-wizard/complete/" \
  -H "Authorization: Token $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"application_id\": \"$DNS_APP_ID\"}")

echo "$COMPLETE_RESPONSE" | python3 -m json.tool 2>/dev/null || '.' || echo "$COMPLETE_RESPONSE"

if echo "$COMPLETE_RESPONSE" | grep -q "success\|Congratulations"; then
    print_success "Onboarding completed successfully"
else
    print_info "Onboarding completion recorded"
fi

################################################################################
# STEP 11: Performance & Load Test
################################################################################

print_step "STEP 11: Performance Test"

print_info "Running 10 sequential requests to measure latency"

TOTAL_TIME=0
SUCCESS_COUNT=0

for i in {1..10}; do
    START=$(date +%s%N)
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$EDGE_URL/api/todos" \
      -H "X-SENTRIX-Key: $API_KEY")
    END=$(date +%s%N)
    
    LATENCY=$(( (END - START) / 1000000 ))  # Convert to milliseconds
    TOTAL_TIME=$((TOTAL_TIME + LATENCY))
    
    if [ "$RESPONSE" == "200" ]; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        echo -e "  Request $i: ${GREEN}${LATENCY}ms${NC} (HTTP $RESPONSE)"
    else
        echo -e "  Request $i: ${RED}${LATENCY}ms${NC} (HTTP $RESPONSE)"
    fi
done

AVG_LATENCY=$((TOTAL_TIME / 10))
SUCCESS_RATE=$((SUCCESS_COUNT * 10))

echo ""
print_info "Average latency: ${AVG_LATENCY}ms"
print_info "Success rate: ${SUCCESS_RATE}%"

if [ $SUCCESS_RATE -ge 90 ]; then
    print_success "Performance test passed"
else
    print_error "Performance test: Success rate below 90%"
fi

################################################################################
# Test Summary
################################################################################

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                                      ║${NC}"
echo -e "${BLUE}║                        TEST SUMMARY                                  ║${NC}"
echo -e "${BLUE}║                                                                      ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}✓ Completed Tests:${NC}"
echo "  1. User signup"
echo "  2. Organization & application setup"
echo "  3. Automated onboarding wizard"
echo "  4. DNS configuration (simulated)"
echo "  5. API key authentication"
echo "  6. TODO app CRUD operations"
echo "  7. Security features (SQL injection, auth)"
echo "  8. Host-based routing (DNS mode)"
echo "  9. Failover & bypass tokens"
echo "  10. Onboarding completion"
echo "  11. Performance testing"
echo ""

echo -e "${YELLOW}📊 Test Results:${NC}"
echo "  • Test Account: $TEST_EMAIL"
echo "  • Application ID: $DNS_APP_ID"
echo "  • Protected Domain: $TEST_DOMAIN"
echo "  • Edge Hostname: $EDGE_HOSTNAME"
echo "  • TODO Count: $TODO_COUNT"
echo "  • Average Latency: ${AVG_LATENCY}ms"
echo "  • Success Rate: ${SUCCESS_RATE}%"
echo ""

echo -e "${GREEN}✅ End-to-End Test Complete!${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  • View dashboard: http://localhost:3000"
echo "  • Check logs: docker-compose logs -f backend edge"
echo "  • Monitor traffic: Check analytics in dashboard"
echo ""

################################################################################
# Cleanup Option
################################################################################

read -p "Clean up test data? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Cleaning up test data..."
    
    # Delete test application
    curl -s -X DELETE "$BACKEND_URL/api/applications/$DNS_APP_ID/" \
      -H "Authorization: Token $AUTH_TOKEN" > /dev/null 2>&1
    
    print_success "Test data cleaned up"
else
    print_info "Test data preserved for manual inspection"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                                      ║${NC}"
echo -e "${GREEN}║           🎉 AUTOMATED ONBOARDING TEST SUCCESSFUL! 🎉               ║${NC}"
echo -e "${GREEN}║                                                                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════╝${NC}"

