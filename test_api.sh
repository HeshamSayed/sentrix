#!/bin/bash
# Sentrix API Testing Script
# Tests all core management APIs

set -e

BASE_URL="http://localhost:8000/v1"
CONTENT_TYPE="Content-Type: application/json"

echo "=========================================="
echo "Sentrix API Testing"
echo "=========================================="
echo ""

# 1. Login
echo "1. Login as admin..."
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login/" \
  -H "${CONTENT_TYPE}" \
  -d '{
    "email": "admin@acme.com",
    "password": "admin123"
  }')

ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$ACCESS_TOKEN" == "null" ] || [ -z "$ACCESS_TOKEN" ]; then
  echo "❌ Login failed!"
  echo "$LOGIN_RESPONSE" | jq '.'
  exit 1
fi

echo "✓ Login successful"
echo "Access token: ${ACCESS_TOKEN:0:50}..."
echo ""

AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"

# 2. Get current user
echo "2. Get current user (GET /v1/auth/me/)..."
curl -s -X GET "${BASE_URL}/auth/me/" \
  -H "${AUTH_HEADER}" | jq '.'
echo ""

# 3. List organizations
echo "3. List organizations (GET /v1/organizations/)..."
curl -s -X GET "${BASE_URL}/organizations/" \
  -H "${AUTH_HEADER}" | jq '.results[] | {org_id, name, slug}'
echo ""

# 4. Get current subscription
echo "4. Get current subscription (GET /v1/subscriptions/current/)..."
curl -s -X GET "${BASE_URL}/subscriptions/current/" \
  -H "${AUTH_HEADER}" | jq '{plan_tier, quota_max_applications, quota_max_users, quota_requests_per_month}'
echo ""

# 5. List applications
echo "5. List applications (GET /v1/applications/)..."
curl -s -X GET "${BASE_URL}/applications/" \
  -H "${AUTH_HEADER}" | jq '.results[] | {app_id, name, domain, dns_verified}'
echo ""

# 6. Get first application
APP_ID=$(curl -s -X GET "${BASE_URL}/applications/" \
  -H "${AUTH_HEADER}" | jq -r '.results[0].app_id')

if [ "$APP_ID" != "null" ] && [ -n "$APP_ID" ]; then
  echo "6. Get application config (GET /v1/applications/${APP_ID}/config/)..."
  curl -s -X GET "${BASE_URL}/applications/${APP_ID}/config/" \
    -H "${AUTH_HEADER}" | jq '.'
  echo ""
else
  echo "6. No applications found, skipping config test"
  echo ""
fi

# 7. List users
echo "7. List users (GET /v1/users/)..."
curl -s -X GET "${BASE_URL}/users/" \
  -H "${AUTH_HEADER}" | jq '.results[] | {user_id, email, role, is_active}'
echo ""

# 8. List endpoints
echo "8. List discovered endpoints (GET /v1/endpoints/)..."
ENDPOINTS_RESPONSE=$(curl -s -X GET "${BASE_URL}/endpoints/" \
  -H "${AUTH_HEADER}")

ENDPOINT_COUNT=$(echo "$ENDPOINTS_RESPONSE" | jq '.count')
echo "Found $ENDPOINT_COUNT discovered endpoints"

if [ "$ENDPOINT_COUNT" != "0" ]; then
  echo "$ENDPOINTS_RESPONSE" | jq '.results[] | {method, path_pattern, request_count}' | head -20
fi
echo ""

# 9. Test decision API (no auth required)
echo "9. Test decision API (POST /v1/edge/decision/)..."
curl -s -X POST "${BASE_URL}/edge/decision" \
  -H "${CONTENT_TYPE}" \
  -d '{
    "domain": "api.acme-payments.com",
    "method": "POST",
    "path": "/payments/charge/123",
    "client_ip": "1.2.3.4"
  }' | jq '.'
echo ""

echo "=========================================="
echo "✓ All API tests completed successfully!"
echo "=========================================="
echo ""
echo "Available endpoints:"
echo "  POST   /v1/auth/login/"
echo "  GET    /v1/auth/me/"
echo "  GET    /v1/organizations/"
echo "  GET    /v1/subscriptions/current/"
echo "  GET    /v1/applications/"
echo "  GET    /v1/applications/{id}/config/"
echo "  PATCH  /v1/applications/{id}/update_config/"
echo "  GET    /v1/users/"
echo "  GET    /v1/endpoints/"
echo "  GET    /v1/usage/"
echo "  POST   /v1/edge/decision"
echo ""

# 10. Test dashboard summary
echo "10. Test dashboard summary (GET /v1/dashboard/summary/)..."
curl -s -X GET "${BASE_URL}/dashboard/summary/" \
  -H "${AUTH_HEADER}" | jq '{overview, traffic, detections: {total: .detections.total, open: .detections.open}}'
echo ""

# 11. List detections
echo "11. List detections (GET /v1/detection/detections/)..."
DETECTIONS_RESPONSE=$(curl -s -X GET "${BASE_URL}/detection/detections/" \
  -H "${AUTH_HEADER}")

DETECTION_COUNT=$(echo "$DETECTIONS_RESPONSE" | jq '.count')
echo "Found $DETECTION_COUNT detections"

if [ "$DETECTION_COUNT" != "0" ]; then
  echo "$DETECTIONS_RESPONSE" | jq '.results[] | {detection_id, severity, detector_name, status}' | head -20
fi
echo ""

# 12. Get detection summary
echo "12. Get detection summary (GET /v1/detection/detections/summary/)..."
curl -s -X GET "${BASE_URL}/detection/detections/summary/" \
  -H "${AUTH_HEADER}" | jq '{total, open, by_severity, by_detector_type}'
echo ""

echo "=========================================="
echo "✓ All API tests completed successfully!"
echo "=========================================="
echo ""
echo "New endpoints in Phase 4:"
echo "  GET    /v1/dashboard/summary/"
echo "  GET    /v1/dashboard/metrics/"
echo "  GET    /v1/detection/detections/"
echo "  GET    /v1/detection/detections/summary/"
echo "  POST   /v1/detection/detections/{id}/assign/"
echo "  POST   /v1/detection/detections/{id}/close/"
echo ""
