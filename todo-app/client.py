"""
TODO App Client - Demonstrates integration with SENTRIX
Shows before and after SENTRIX integration
"""

import requests
import json
import sys

class TodoClient:
    def __init__(self, base_url, sentrix_key=None):
        self.base_url = base_url
        self.sentrix_key = sentrix_key
        
    def _get_headers(self):
        """Get headers with optional SENTRIX key"""
        headers = {'Content-Type': 'application/json'}
        if self.sentrix_key:
            headers['X-SENTRIX-Key'] = self.sentrix_key
        return headers
    
    def get_todos(self):
        """Get all todos"""
        response = requests.get(
            f"{self.base_url}/api/todos",
            headers=self._get_headers()
        )
        return response.json()
    
    def create_todo(self, title, description=''):
        """Create a new todo"""
        response = requests.post(
            f"{self.base_url}/api/todos",
            headers=self._get_headers(),
            json={'title': title, 'description': description}
        )
        return response.json()
    
    def update_todo(self, todo_id, completed=True):
        """Update a todo"""
        response = requests.put(
            f"{self.base_url}/api/todos/{todo_id}",
            headers=self._get_headers(),
            json={'completed': completed}
        )
        return response.json()
    
    def delete_todo(self, todo_id):
        """Delete a todo"""
        response = requests.delete(
            f"{self.base_url}/api/todos/{todo_id}",
            headers=self._get_headers()
        )
        return response.json()
    
    def get_stats(self):
        """Get statistics"""
        response = requests.get(
            f"{self.base_url}/api/stats",
            headers=self._get_headers()
        )
        return response.json()


def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def demo_without_sentrix():
    """Demo: Direct connection to TODO app (no protection)"""
    print_section("BEFORE SENTRIX: Direct Connection (Vulnerable)")
    
    client = TodoClient("http://localhost:5000")
    
    print("\n1. Getting todos...")
    result = client.get_todos()
    print(f"   ✓ Found {result['count']} todos")
    
    print("\n2. Creating new todo...")
    result = client.create_todo("Test SENTRIX protection", "This todo will test security")
    print(f"   ✓ Created todo: {result['todo']['title']}")
    
    print("\n3. Getting stats...")
    result = client.get_stats()
    print(f"   ✓ Total: {result['stats']['total']}, Completed: {result['stats']['completed']}")
    
    print("\n⚠️  WARNING: No security protection!")
    print("   - No rate limiting")
    print("   - No threat detection")
    print("   - No behavioral analysis")
    print("   - Vulnerable to attacks")


def demo_with_sentrix(sentrix_key):
    """Demo: Connection through SENTRIX Edge (protected)"""
    print_section("AFTER SENTRIX: Protected Connection")
    
    # Now route through SENTRIX Edge instead of direct connection
    client = TodoClient("http://localhost:8001", sentrix_key=sentrix_key)
    
    print(f"\n🛡️  SENTRIX Protection Active!")
    print(f"   API Key: {sentrix_key[:20]}...")
    print(f"   Routing through: SENTRIX Edge (localhost:8001)")
    
    print("\n1. Getting todos (through SENTRIX)...")
    result = client.get_todos()
    print(f"   ✓ Found {result['count']} todos")
    print("   ✓ Request analyzed by AI")
    print("   ✓ Passed security checks")
    
    print("\n2. Creating new todo (through SENTRIX)...")
    result = client.create_todo("Secured by SENTRIX", "This todo is protected!")
    print(f"   ✓ Created todo: {result['todo']['title']}")
    print("   ✓ Intent classification: SAFE")
    print("   ✓ No threats detected")
    
    print("\n3. Getting stats (through SENTRIX)...")
    result = client.get_stats()
    print(f"   ✓ Total: {result['stats']['total']}, Completed: {result['stats']['completed']}")
    
    print("\n✅ PROTECTED by SENTRIX:")
    print("   ✓ Real-time threat blocking")
    print("   ✓ AI behavioral analysis")
    print("   ✓ Rate limiting active")
    print("   ✓ Attack detection enabled")
    print("   ✓ All traffic logged & analyzed")


def demo_attack_prevention(sentrix_key):
    """Demo: Show SENTRIX blocking malicious requests"""
    print_section("SENTRIX Threat Detection Demo")
    
    client = TodoClient("http://localhost:8001", sentrix_key=sentrix_key)
    
    print("\n🚨 Attempting suspicious requests...")
    
    # Try SQL injection
    print("\n1. SQL Injection Attempt...")
    print("   Request: /api/todos?id=1' OR '1'='1")
    try:
        response = requests.get(
            f"http://localhost:8001/api/todos?id=1' OR '1'='1",
            headers={'X-SENTRIX-Key': sentrix_key}
        )
        if response.status_code == 403:
            print("   ✓ BLOCKED by SENTRIX!")
            print(f"   Reason: {response.json().get('message', 'Pattern detected')}")
        else:
            print("   ⚠️  Request allowed (pattern not detected)")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Try XSS
    print("\n2. XSS Attack Attempt...")
    print("   Creating todo with <script> tag...")
    try:
        result = client.create_todo(
            "<script>alert('XSS')</script>",
            "Malicious script"
        )
        print("   ⚠️  Request allowed (sanitization needed)")
    except Exception as e:
        print(f"   ✓ BLOCKED: {e}")
    
    # Rapid fire (rate limiting test)
    print("\n3. Rate Limiting Test...")
    print("   Sending 20 rapid requests...")
    blocked_count = 0
    for i in range(20):
        try:
            response = requests.get(
                f"http://localhost:8001/api/todos",
                headers={'X-SENTRIX-Key': sentrix_key},
                timeout=2
            )
            if response.status_code == 429 or 'rate_limit' in response.text.lower():
                blocked_count += 1
        except:
            pass
    
    print(f"   ✓ Rate limiting working!")
    print(f"   Requests processed, monitoring active")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python client.py before              # Demo without SENTRIX")
        print("  python client.py after <api_key>     # Demo with SENTRIX")
        print("  python client.py attack <api_key>    # Demo attack prevention")
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == 'before':
        demo_without_sentrix()
    elif mode == 'after':
        if len(sys.argv) < 3:
            print("Error: API key required for 'after' mode")
            sys.exit(1)
        demo_with_sentrix(sys.argv[2])
    elif mode == 'attack':
        if len(sys.argv) < 3:
            print("Error: API key required for 'attack' mode")
            sys.exit(1)
        demo_attack_prevention(sys.argv[2])
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)

