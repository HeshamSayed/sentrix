#!/usr/bin/env python3
"""
Integration tests for Sentrix.
Tests the full pipeline from API to database.
"""

import os
import sys
import time
import json
import requests
from datetime import datetime

# Configuration
BASE_URL = os.getenv('SENTRIX_BASE_URL', 'http://localhost:8000')
MODEL_SERVER_URL = os.getenv('MODEL_SERVER_URL', 'http://localhost:8001')

# Test credentials (from create_test_data)
TEST_ADMIN_EMAIL = 'admin@acme.com'
TEST_ADMIN_PASSWORD = 'admin123'

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class IntegrationTests:
    """Integration test suite for Sentrix."""

    def __init__(self):
        self.token = None
        self.org_id = None
        self.app_id = None
        self.policy_id = None
        self.passed = 0
        self.failed = 0

    def log(self, message, color=RESET):
        """Print colored log message."""
        print(f"{color}{message}{RESET}")

    def log_success(self, message):
        """Print success message."""
        self.log(f"✓ {message}", GREEN)
        self.passed += 1

    def log_error(self, message):
        """Print error message."""
        self.log(f"✗ {message}", RED)
        self.failed += 1

    def log_info(self, message):
        """Print info message."""
        self.log(f"ℹ {message}", BLUE)

    def log_warning(self, message):
        """Print warning message."""
        self.log(f"⚠ {message}", YELLOW)

    def test_health_checks(self):
        """Test health endpoints."""
        self.log_info("\n=== Testing Health Checks ===")

        # Test control plane health
        try:
            response = requests.get(f"{BASE_URL}/health/", timeout=5)
            if response.status_code == 200:
                self.log_success("Control plane health check passed")
            else:
                self.log_error(f"Control plane health check failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"Control plane health check failed: {e}")

        # Test model server health
        try:
            response = requests.get(f"{MODEL_SERVER_URL}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_success(f"Model server health check passed (model: {data.get('model')})")
            else:
                self.log_error(f"Model server health check failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"Model server health check failed: {e}")

    def test_authentication(self):
        """Test authentication flow."""
        self.log_info("\n=== Testing Authentication ===")

        try:
            response = requests.post(
                f"{BASE_URL}/v1/auth/login/",
                json={
                    "email": TEST_ADMIN_EMAIL,
                    "password": TEST_ADMIN_PASSWORD
                },
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get('access_token')
                user = data.get('user', {})
                self.org_id = user.get('org')

                if self.token:
                    self.log_success(f"Authentication successful (user: {user.get('email')})")
                    self.log_success(f"Token received: {self.token[:20]}...")
                else:
                    self.log_error("Authentication response missing token")
            else:
                self.log_error(f"Authentication failed: {response.status_code} - {response.text}")

        except Exception as e:
            self.log_error(f"Authentication failed: {e}")

    def test_organization_api(self):
        """Test organization APIs."""
        self.log_info("\n=== Testing Organization APIs ===")

        if not self.token:
            self.log_warning("Skipping (no auth token)")
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # List organizations
        try:
            response = requests.get(f"{BASE_URL}/v1/organizations/", headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                orgs = data.get('results', [])
                if orgs:
                    org = orgs[0]
                    self.org_id = org['org_id']
                    self.log_success(f"Listed organizations: {len(orgs)} found")
                    self.log_info(f"  Organization: {org['name']} ({org['org_id']})")
                else:
                    self.log_error("No organizations found")
            else:
                self.log_error(f"List organizations failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"List organizations failed: {e}")

        # Get quota summary
        if self.org_id:
            try:
                response = requests.get(
                    f"{BASE_URL}/v1/organizations/{self.org_id}/quota_summary/",
                    headers=headers,
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    apps = data.get('applications', {})
                    self.log_success(f"Quota summary retrieved")
                    self.log_info(f"  Applications: {apps.get('current')}/{apps.get('limit')}")
                else:
                    self.log_error(f"Quota summary failed: {response.status_code}")
            except Exception as e:
                self.log_error(f"Quota summary failed: {e}")

    def test_application_api(self):
        """Test application APIs."""
        self.log_info("\n=== Testing Application APIs ===")

        if not self.token:
            self.log_warning("Skipping (no auth token)")
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # List applications
        try:
            response = requests.get(f"{BASE_URL}/v1/applications/", headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                apps = data.get('results', [])
                if apps:
                    app = apps[0]
                    self.app_id = app['app_id']
                    self.log_success(f"Listed applications: {len(apps)} found")
                    self.log_info(f"  Application: {app['name']} ({app['app_id']})")
                    self.log_info(f"  Domain: {app['domain']}")
                else:
                    self.log_error("No applications found")
            else:
                self.log_error(f"List applications failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"List applications failed: {e}")

        # Get application config
        if self.app_id:
            try:
                response = requests.get(
                    f"{BASE_URL}/v1/applications/{self.app_id}/config/",
                    headers=headers,
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    merged = data.get('merged_config', {})
                    self.log_success("Application config retrieved")
                    self.log_info(f"  Rate limit: {merged.get('rate_limit_rpm')} rpm")
                else:
                    self.log_error(f"Application config failed: {response.status_code}")
            except Exception as e:
                self.log_error(f"Application config failed: {e}")

    def test_decision_api(self):
        """Test decision API."""
        self.log_info("\n=== Testing Decision API ===")

        if not self.app_id:
            self.log_warning("Skipping (no app_id)")
            return

        # Test decision API (no auth required - internal endpoint)
        try:
            response = requests.post(
                f"{BASE_URL}/v1/edge/decision",
                json={
                    "domain": "api.acme-payments.com",
                    "method": "GET",
                    "path": "/api/test",
                    "client_ip": "192.168.1.100"
                },
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                action = data.get('action')
                reason = data.get('reason')
                score = data.get('score')
                self.log_success(f"Decision API call successful")
                self.log_info(f"  Action: {action}")
                self.log_info(f"  Reason: {reason}")
                self.log_info(f"  Score: {score}")
            else:
                self.log_error(f"Decision API failed: {response.status_code} - {response.text}")

        except Exception as e:
            self.log_error(f"Decision API failed: {e}")

    def test_policy_engine(self):
        """Test policy engine."""
        self.log_info("\n=== Testing Policy Engine ===")

        if not self.token or not self.app_id:
            self.log_warning("Skipping (no auth token or app_id)")
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # Test policy DSL
        try:
            response = requests.post(
                f"{BASE_URL}/v1/policy/test/",
                json={
                    "condition": {
                        "field": "path",
                        "op": "startswith",
                        "value": "/admin"
                    },
                    "events": [
                        {"method": "GET", "path": "/admin/users"},
                        {"method": "GET", "path": "/api/users"}
                    ]
                },
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                matched = data.get('matched', 0)
                total = data.get('total_events', 0)
                self.log_success(f"Policy DSL test successful")
                self.log_info(f"  Matched: {matched}/{total} events")
            else:
                self.log_error(f"Policy DSL test failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"Policy DSL test failed: {e}")

        # List policies
        try:
            response = requests.get(
                f"{BASE_URL}/v1/policy/policies/",
                headers=headers,
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                policies = data.get('results', [])
                self.log_success(f"Listed policies: {len(policies)} found")

                if policies:
                    policy = policies[0]
                    self.policy_id = policy['policy_id']
                    self.log_info(f"  Policy: {policy['name']}")
                    self.log_info(f"  Mode: {policy['mode']}, Enabled: {policy['is_enabled']}")

            else:
                self.log_error(f"List policies failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"List policies failed: {e}")

    def test_detection_api(self):
        """Test detection APIs."""
        self.log_info("\n=== Testing Detection APIs ===")

        if not self.token:
            self.log_warning("Skipping (no auth token)")
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # List detections
        try:
            response = requests.get(
                f"{BASE_URL}/v1/detection/detections/",
                headers=headers,
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                detections = data.get('results', [])
                self.log_success(f"Listed detections: {len(detections)} found")

                if detections:
                    detection = detections[0]
                    self.log_info(f"  Detection: {detection['detector_name']}")
                    self.log_info(f"  Severity: {detection['severity']}")
                    self.log_info(f"  Status: {detection['status']}")

            else:
                self.log_error(f"List detections failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"List detections failed: {e}")

        # Get detection summary
        try:
            response = requests.get(
                f"{BASE_URL}/v1/detection/detections/summary/",
                headers=headers,
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                total = data.get('total', 0)
                by_severity = data.get('by_severity', {})
                self.log_success(f"Detection summary retrieved")
                self.log_info(f"  Total: {total}")
                self.log_info(f"  By severity: {by_severity}")
            else:
                self.log_error(f"Detection summary failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"Detection summary failed: {e}")

    def test_dashboard_api(self):
        """Test dashboard APIs."""
        self.log_info("\n=== Testing Dashboard APIs ===")

        if not self.token:
            self.log_warning("Skipping (no auth token)")
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # Get dashboard summary
        try:
            response = requests.get(
                f"{BASE_URL}/v1/dashboard/summary/",
                headers=headers,
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                overview = data.get('overview', {})
                traffic = data.get('traffic', {})
                detections = data.get('detections', {})

                self.log_success("Dashboard summary retrieved")
                self.log_info(f"  Applications: {overview.get('total_applications')}")
                self.log_info(f"  Users: {overview.get('total_users')}")
                self.log_info(f"  Endpoints: {overview.get('total_endpoints')}")
                self.log_info(f"  Requests (24h): {traffic.get('requests_24h')}")
                self.log_info(f"  Detections: {detections.get('total')}")
            else:
                self.log_error(f"Dashboard summary failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"Dashboard summary failed: {e}")

    def run_all_tests(self):
        """Run all integration tests."""
        self.log(f"\n{'='*60}", BLUE)
        self.log(f"SENTRIX INTEGRATION TESTS", BLUE)
        self.log(f"{'='*60}\n", BLUE)
        self.log_info(f"Base URL: {BASE_URL}")
        self.log_info(f"Model Server: {MODEL_SERVER_URL}")
        self.log_info(f"Timestamp: {datetime.now().isoformat()}")

        # Run tests
        self.test_health_checks()
        self.test_authentication()
        self.test_organization_api()
        self.test_application_api()
        self.test_decision_api()
        self.test_policy_engine()
        self.test_detection_api()
        self.test_dashboard_api()

        # Summary
        self.log(f"\n{'='*60}", BLUE)
        self.log(f"TEST SUMMARY", BLUE)
        self.log(f"{'='*60}\n", BLUE)

        total = self.passed + self.failed
        self.log_success(f"Passed: {self.passed}/{total}")

        if self.failed > 0:
            self.log_error(f"Failed: {self.failed}/{total}")
            return 1
        else:
            self.log_success("All tests passed! ✨")
            return 0


if __name__ == '__main__':
    tests = IntegrationTests()
    exit_code = tests.run_all_tests()
    sys.exit(exit_code)
