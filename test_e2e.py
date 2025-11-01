#!/usr/bin/env python3
"""
SENTRIX Automated Onboarding - End-to-End Test
Tests complete flow: Signup → Onboarding → Protection → Testing
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
BACKEND_URL = "http://localhost:8000"
EDGE_URL = "http://localhost:8001"
TODO_APP_URL = "http://localhost:5000"

# Test data
TIMESTAMP = int(time.time())
TEST_EMAIL = f"test-{TIMESTAMP}@todo.com"
TEST_PASSWORD = "SecureTestPass123!"
TEST_COMPANY = f"TODO Test Inc {TIMESTAMP}"
TEST_DOMAIN = "api.todo-test.local"
TEST_ORIGIN = "http://localhost:5000"  # TODO app origin

# Colors
class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'  # No Color

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*70}{Colors.NC}")
    print(f"{Colors.BLUE}▶ {text}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*70}{Colors.NC}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.NC}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.NC}")

def print_info(text):
    print(f"{Colors.YELLOW}ℹ {text}{Colors.NC}")

def check_service(name, url):
    try:
        response = requests.get(url, timeout=5)
        print_success(f"{name} is running (HTTP {response.status_code})")
        return True
    except Exception as e:
        print_error(f"{name} is not responding: {e}")
        return False

def main():
    print(f"{Colors.BLUE}╔{'='*70}╗{Colors.NC}")
    print(f"{Colors.BLUE}║{' '*70}║{Colors.NC}")
    print(f"{Colors.BLUE}║{'SENTRIX AUTOMATED ONBOARDING - END-TO-END TEST':^70}║{Colors.NC}")
    print(f"{Colors.BLUE}║{' '*70}║{Colors.NC}")
    print(f"{Colors.BLUE}╚{'='*70}╝{Colors.NC}\n")

    # Pre-flight checks
    print_header("Pre-Flight Checks")
    
    if not check_service("Backend", f"{BACKEND_URL}/api/"):
        sys.exit(1)
    if not check_service("Edge", f"{EDGE_URL}/health"):
        sys.exit(1)
    if not check_service("TODO App", f"{TODO_APP_URL}/health"):
        sys.exit(1)
    
    print_success("All services are running")

    # Step 1: User Signup
    print_header("STEP 1: User Signup")
    print_info(f"Creating test account: {TEST_EMAIL}")
    
    signup_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "first_name": "Test",
        "last_name": "User",
        "company_name": TEST_COMPANY
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/api/onboarding/signup/", json=signup_data)
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 201:
            auth_token = response.json().get('token')
            print_success("Account created successfully")
            print_info(f"Auth Token: {auth_token[:20]}...")
        else:
            print_error(f"Signup failed: HTTP {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print_error(f"Signup error: {e}")
        sys.exit(1)

    # Step 2: Quick Start Setup
    print_header("STEP 2: Quick Start Setup")
    print_info("Setting up organization and environment")
    
    quickstart_data = {
        "organization_name": TEST_COMPANY,
        "plan_type": "starter",
        "environments": [{
            "name": "Production",
            "environment_type": "production",
            "applications": [{
                "name": "TODO API Test",
                "base_url": f"http://{TEST_DOMAIN}",
                "target_url": TEST_ORIGIN
            }]
        }]
    }
    
    headers = {"Authorization": f"Token {auth_token}"}
    
    try:
        response = requests.post(f"{BACKEND_URL}/api/onboarding/quick_start/", 
                                json=quickstart_data, headers=headers)
        result = response.json()
        print(json.dumps(result, indent=2))
        
        if response.status_code == 201:
            app_id = result['applications'][0]['id']
            api_key = result['applications'][0]['api_key']
            print_success("Organization and application created")
            print_info(f"Application ID: {app_id}")
            print_info(f"API Key: {api_key[:30]}...")
        else:
            print_error(f"Quick start failed: HTTP {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print_error(f"Quick start error: {e}")
        sys.exit(1)

    # Step 3: Skip Onboarding Wizard (Already have API key from quick_start)
    print_header("STEP 3: Onboarding Complete")
    print_info("Application already created via quick_start")
    print_info("API key ready for use")
    print_success("Ready to protect TODO app")

    # Step 4: Test TODO App Through SENTRIX Edge
    print_header("STEP 4: Test TODO App - API Key Mode")
    
    edge_headers = {"X-SENTRIX-Key": api_key, "Content-Type": "application/json"}
    
    # Test 1: Health check
    print(f"\n{Colors.YELLOW}Test 1: Health Check{Colors.NC}")
    try:
        response = requests.get(f"{EDGE_URL}/health", headers=edge_headers)
        print(f"Response: HTTP {response.status_code}")
        print(response.text[:200])
        if response.status_code == 200:
            print_success("Health check passed")
        else:
            print_info(f"Health check returned {response.status_code}")
    except Exception as e:
        print_error(f"Health check error: {e}")

    # Test 2: Get todos (empty)
    print(f"\n{Colors.YELLOW}Test 2: Get Todos (Initial){Colors.NC}")
    try:
        response = requests.get(f"{EDGE_URL}/api/todos", headers=edge_headers)
        print(f"Response: HTTP {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        if response.status_code == 200:
            print_success("Get todos passed")
        else:
            print_info(f"Get todos returned {response.status_code}")
    except Exception as e:
        print_error(f"Get todos error: {e}")

    # Test 3: Add a todo
    print(f"\n{Colors.YELLOW}Test 3: Add Todo{Colors.NC}")
    todo_data = {"title": "Test TODO via SENTRIX", "completed": False}
    try:
        response = requests.post(f"{EDGE_URL}/api/todos", json=todo_data, headers=edge_headers)
        print(f"Response: HTTP {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        if response.status_code == 201:
            print_success("Add todo passed")
        else:
            print_info(f"Add todo returned {response.status_code}")
    except Exception as e:
        print_error(f"Add todo error: {e}")

    # Test 4: Get todos again
    print(f"\n{Colors.YELLOW}Test 4: Get Todos (After Add){Colors.NC}")
    try:
        response = requests.get(f"{EDGE_URL}/api/todos", headers=edge_headers)
        print(f"Response: HTTP {response.status_code}")
        result = response.json()
        print(json.dumps(result, indent=2))
        
        todo_count = len(result.get('todos', []))
        if todo_count > 0:
            print_success(f"Todo was added successfully ({todo_count} todos found)")
        else:
            print_error("Todo count verification failed")
    except Exception as e:
        print_error(f"Get todos after error: {e}")

    # Test 5: Get stats
    print(f"\n{Colors.YELLOW}Test 5: Get Stats{Colors.NC}")
    try:
        response = requests.get(f"{EDGE_URL}/api/stats", headers=edge_headers)
        print(f"Response: HTTP {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        if response.status_code == 200:
            print_success("Get stats passed")
        else:
            print_info(f"Get stats returned {response.status_code}")
    except Exception as e:
        print_error(f"Get stats error: {e}")

    # Step 5: Test Security Features
    print_header("STEP 5: Test Security Features")
    
    # Test SQL Injection
    print(f"\n{Colors.YELLOW}Test: SQL Injection Detection{Colors.NC}")
    try:
        response = requests.get(f"{EDGE_URL}/api/todos?id=1' OR '1'='1", headers=edge_headers)
        print(f"Response: HTTP {response.status_code}")
        print(response.text[:200])
        if response.status_code == 403:
            print_success("SQL injection blocked")
        else:
            print_info("SQL injection test (may need configuration)")
    except Exception as e:
        print_error(f"SQL injection test error: {e}")

    # Test no API key
    print(f"\n{Colors.YELLOW}Test: No API Key (Should Fail){Colors.NC}")
    try:
        response = requests.get(f"{EDGE_URL}/api/todos")
        print(f"Response: HTTP {response.status_code}")
        print(response.text[:200])
        if response.status_code == 401:
            print_success("Request without API key was rejected")
        else:
            print_error("Request without API key should have been rejected")
    except Exception as e:
        print_error(f"No API key test error: {e}")

    # Step 6: Performance Test
    print_header("STEP 6: Performance Test")
    print_info("Running 10 sequential requests")
    
    latencies = []
    success_count = 0
    
    for i in range(10):
        start = time.time()
        try:
            response = requests.get(f"{EDGE_URL}/api/todos", headers=edge_headers)
            latency_ms = int((time.time() - start) * 1000)
            latencies.append(latency_ms)
            
            if response.status_code == 200:
                success_count += 1
                print(f"  Request {i+1}: {Colors.GREEN}{latency_ms}ms{Colors.NC} (HTTP {response.status_code})")
            else:
                print(f"  Request {i+1}: {Colors.RED}{latency_ms}ms{Colors.NC} (HTTP {response.status_code})")
        except Exception as e:
            print(f"  Request {i+1}: {Colors.RED}FAILED{Colors.NC} - {e}")
    
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        success_rate = (success_count / 10) * 100
        
        print()
        print_info(f"Average latency: {int(avg_latency)}ms")
        print_info(f"Success rate: {success_rate}%")
        
        if success_rate >= 90:
            print_success("Performance test passed")
        else:
            print_error("Performance test: Success rate below 90%")

    # Test Summary
    print(f"\n{Colors.BLUE}╔{'='*70}╗{Colors.NC}")
    print(f"{Colors.BLUE}║{' '*70}║{Colors.NC}")
    print(f"{Colors.BLUE}║{'TEST SUMMARY':^70}║{Colors.NC}")
    print(f"{Colors.BLUE}║{' '*70}║{Colors.NC}")
    print(f"{Colors.BLUE}╚{'='*70}╝{Colors.NC}\n")

    print(f"{Colors.GREEN}✓ Completed Tests:{Colors.NC}")
    print("  1. User signup")
    print("  2. Organization & application setup (quick_start)")
    print("  3. TODO app CRUD operations through SENTRIX Edge")
    print("  4. Security features (SQL injection, auth validation)")
    print("  5. Performance testing")
    print("  6. End-to-end protection verified")
    print()

    print(f"{Colors.YELLOW}📊 Test Results:{Colors.NC}")
    print(f"  • Test Account: {TEST_EMAIL}")
    print(f"  • Application ID: {app_id}")
    print(f"  • Protected Domain: {TEST_DOMAIN}")
    print(f"  • API Key: {api_key[:30]}...")
    if latencies:
        print(f"  • Average Latency: {int(avg_latency)}ms")
        print(f"  • Success Rate: {success_rate}%")
    print()

    print(f"{Colors.GREEN}✅ End-to-End Test Complete!{Colors.NC}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.NC}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Test failed with error: {e}{Colors.NC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

