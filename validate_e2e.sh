#!/bin/bash
#
# End-to-end validation script for Sentrix
# Tests the complete flow from edge to database
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${SENTRIX_BASE_URL:-http://localhost:8000}"
DOCKER_COMPOSE="${DOCKER_COMPOSE:-docker compose}"

# Counters
PASSED=0
FAILED=0

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
    ((PASSED++))
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
    ((FAILED++))
}

log_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

log_header() {
    echo ""
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
}

check_service() {
    local service=$1
    if $DOCKER_COMPOSE ps | grep -q "$service.*Up"; then
        log_success "Service $service is running"
        return 0
    else
        log_error "Service $service is not running"
        return 1
    fi
}

check_health() {
    local url=$1
    local name=$2
    if curl -sf "$url" > /dev/null 2>&1; then
        log_success "$name health check passed"
        return 0
    else
        log_error "$name health check failed"
        return 1
    fi
}

# Main validation flow
main() {
    log_header "SENTRIX END-TO-END VALIDATION"
    log_info "Base URL: $BASE_URL"
    log_info "Timestamp: $(date -Iseconds)"
    echo ""

    # Step 1: Check Docker services
    log_header "Step 1: Checking Docker Services"
    check_service "control-plane"
    check_service "postgres"
    check_service "redis"
    check_service "kafka"
    check_service "zookeeper"
    check_service "model-server"
    check_service "enrichment-consumer"
    check_service "detector-consumer"

    # Step 2: Health checks
    log_header "Step 2: Health Checks"
    check_health "$BASE_URL/health/" "Control Plane"
    check_health "http://localhost:8001/health" "Model Server"

    # Step 3: Database connectivity
    log_header "Step 3: Database Connectivity"
    if $DOCKER_COMPOSE exec -T postgres psql -U sentrix -d sentrix -c "SELECT 1" > /dev/null 2>&1; then
        log_success "PostgreSQL connection successful"
    else
        log_error "PostgreSQL connection failed"
    fi

    # Step 4: Redis connectivity
    log_header "Step 4: Redis Connectivity"
    if $DOCKER_COMPOSE exec -T redis redis-cli PING | grep -q "PONG"; then
        log_success "Redis connection successful"
    else
        log_error "Redis connection failed"
    fi

    # Step 5: Kafka topics
    log_header "Step 5: Kafka Topics"
    if $DOCKER_COMPOSE exec -T kafka kafka-topics --list --bootstrap-server localhost:9092 | grep -q "ingest.events"; then
        log_success "Kafka topic 'ingest.events' exists"
    else
        log_error "Kafka topic 'ingest.events' not found"
    fi

    if $DOCKER_COMPOSE exec -T kafka kafka-topics --list --bootstrap-server localhost:9092 | grep -q "enriched.events"; then
        log_success "Kafka topic 'enriched.events' exists"
    else
        log_error "Kafka topic 'enriched.events' not found"
    fi

    if $DOCKER_COMPOSE exec -T kafka kafka-topics --list --bootstrap-server localhost:9092 | grep -q "detection.events"; then
        log_success "Kafka topic 'detection.events' exists"
    else
        log_error "Kafka topic 'detection.events' not found"
    fi

    # Step 6: Database tables
    log_header "Step 6: Database Tables"
    TABLES=("organization" "subscription" "sentrix_user" "application" "api_endpoint" "api_request_event" "detection_event" "policy")
    for table in "${TABLES[@]}"; do
        if $DOCKER_COMPOSE exec -T postgres psql -U sentrix -d sentrix -c "SELECT 1 FROM $table LIMIT 1" > /dev/null 2>&1; then
            log_success "Table '$table' exists and is accessible"
        else
            log_error "Table '$table' not found or inaccessible"
        fi
    done

    # Step 7: Test data exists
    log_header "Step 7: Test Data Verification"
    ORG_COUNT=$($DOCKER_COMPOSE exec -T postgres psql -U sentrix -d sentrix -t -c "SELECT COUNT(*) FROM organization" | xargs)
    if [ "$ORG_COUNT" -gt 0 ]; then
        log_success "Organizations: $ORG_COUNT found"
    else
        log_warning "No organizations found. Run: python manage.py create_test_data"
    fi

    APP_COUNT=$($DOCKER_COMPOSE exec -T postgres psql -U sentrix -d sentrix -t -c "SELECT COUNT(*) FROM application" | xargs)
    if [ "$APP_COUNT" -gt 0 ]; then
        log_success "Applications: $APP_COUNT found"
    else
        log_warning "No applications found. Run: python manage.py create_test_data"
    fi

    USER_COUNT=$($DOCKER_COMPOSE exec -T postgres psql -U sentrix -d sentrix -t -c "SELECT COUNT(*) FROM sentrix_user" | xargs)
    if [ "$USER_COUNT" -gt 0 ]; then
        log_success "Users: $USER_COUNT found"
    else
        log_warning "No users found. Run: python manage.py create_test_data"
    fi

    # Step 8: API endpoints
    log_header "Step 8: API Endpoints"

    # Health endpoint (no auth)
    if curl -sf "$BASE_URL/health/" > /dev/null 2>&1; then
        log_success "Health endpoint accessible"
    else
        log_error "Health endpoint not accessible"
    fi

    # Decision API endpoint (no auth)
    if curl -sf -X POST "$BASE_URL/v1/edge/decision" \
        -H "Content-Type: application/json" \
        -d '{"domain":"test.com","method":"GET","path":"/","client_ip":"127.0.0.1"}' \
        > /dev/null 2>&1; then
        log_success "Decision API endpoint accessible"
    else
        log_error "Decision API endpoint not accessible"
    fi

    # Step 9: Consumer lag
    log_header "Step 9: Kafka Consumer Status"
    if $DOCKER_COMPOSE exec -T kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list | grep -q "enrichment-group"; then
        log_success "Enrichment consumer group exists"

        # Check lag
        LAG=$($DOCKER_COMPOSE exec -T kafka kafka-consumer-groups \
            --bootstrap-server localhost:9092 \
            --group enrichment-group \
            --describe 2>/dev/null | tail -n +2 | awk '{sum+=$5} END {print sum}' || echo "0")

        if [ "$LAG" = "0" ] || [ -z "$LAG" ]; then
            log_success "Enrichment consumer: no lag"
        else
            log_warning "Enrichment consumer: $LAG messages lag"
        fi
    else
        log_warning "Enrichment consumer group not found (may not have processed events yet)"
    fi

    if $DOCKER_COMPOSE exec -T kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list | grep -q "detector-group"; then
        log_success "Detector consumer group exists"

        # Check lag
        LAG=$($DOCKER_COMPOSE exec -T kafka kafka-consumer-groups \
            --bootstrap-server localhost:9092 \
            --group detector-group \
            --describe 2>/dev/null | tail -n +2 | awk '{sum+=$5} END {print sum}' || echo "0")

        if [ "$LAG" = "0" ] || [ -z "$LAG" ]; then
            log_success "Detector consumer: no lag"
        else
            log_warning "Detector consumer: $LAG messages lag"
        fi
    else
        log_warning "Detector consumer group not found (may not have processed events yet)"
    fi

    # Step 10: Python integration tests
    log_header "Step 10: Running Integration Tests"
    if [ -f "test_integration.py" ]; then
        log_info "Running Python integration tests..."
        if python3 test_integration.py; then
            log_success "Integration tests passed"
        else
            log_error "Integration tests failed"
        fi
    else
        log_warning "test_integration.py not found, skipping"
    fi

    # Summary
    log_header "VALIDATION SUMMARY"
    echo ""
    TOTAL=$((PASSED + FAILED))
    echo -e "${GREEN}Passed: $PASSED/$TOTAL${NC}"

    if [ $FAILED -gt 0 ]; then
        echo -e "${RED}Failed: $FAILED/$TOTAL${NC}"
        echo ""
        log_error "Validation completed with errors"
        exit 1
    else
        echo ""
        log_success "All validations passed! ✨"
        echo ""
        log_info "System Status: READY"
        log_info "Next steps:"
        echo "  1. Run integration tests: python3 test_integration.py"
        echo "  2. View dashboard: open $BASE_URL/admin"
        echo "  3. Check logs: docker compose logs -f control-plane"
        exit 0
    fi
}

# Run validation
main
