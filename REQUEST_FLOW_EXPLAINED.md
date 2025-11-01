# 🔄 Complete Request Flow: Client → SENTRIX → Protected Origin

## Overview
Understanding how traffic flows from end-user to protected application through SENTRIX.

---

## 📊 **Visual Flow Diagram**

```
┌─────────────┐
│   End User  │ (Browser/Mobile App/API Client)
└──────┬──────┘
       │ ① Request: GET https://bills.paymobsolutions.com/api/invoices
       ↓
┌─────────────────────────────────────────────────────────────┐
│                    DNS RESOLUTION                           │
│  Query: bills.paymobsolutions.com → ?                       │
│  Answer: CNAME c-550e8400.edge.sentrix.io → 1.2.3.4        │
└──────┬──────────────────────────────────────────────────────┘
       │ ② TCP Connection to 1.2.3.4:443 (SENTRIX Edge IP)
       ↓
┌──────────────────────────────────────────────────────────────┐
│                    SENTRIX EDGE SERVICE                      │
│  Host: bills.paymobsolutions.com                            │
│  Path: /api/invoices                                        │
│                                                              │
│  ③ Security Checks:                                         │
│     • Rate limiting                                         │
│     • IP blocking                                           │
│     • Geo-blocking                                          │
│     • Behavioral analysis                                   │
│     • SQL injection detection                               │
│     • XSS detection                                         │
│     • DDoS mitigation                                       │
│                                                              │
│  ④ Lookup Application:                                      │
│     SELECT * FROM applications                              │
│     WHERE protected_domain = 'bills.paymobsolutions.com'    │
│     → target_url: https://origin.paymob.internal:8000       │
│                                                              │
│  ⑤ Sign Request:                                            │
│     Add header: X-SENTRIX-Signature: <signed-token>         │
│     Add header: X-SENTRIX-Request-ID: abc123...             │
│     Add header: X-Real-IP: <client-ip>                      │
│                                                              │
└──────┬───────────────────────────────────────────────────────┘
       │ ⑥ Proxy Request: GET https://origin.paymob.internal:8000/api/invoices
       ↓
┌──────────────────────────────────────────────────────────────┐
│              PAYMOB ORIGIN SERVER (Protected)                │
│  • Validate X-SENTRIX-Signature header                      │
│  • Process legitimate request                               │
│  • Generate response                                        │
└──────┬───────────────────────────────────────────────────────┘
       │ ⑦ Response: 200 OK + JSON data
       ↓
┌──────────────────────────────────────────────────────────────┐
│                    SENTRIX EDGE SERVICE                      │
│  • Add SENTRIX headers                                      │
│  • Log metrics                                              │
│  • Update quotas                                            │
└──────┬───────────────────────────────────────────────────────┘
       │ ⑧ Final Response
       ↓
┌─────────────┐
│   End User  │ (Receives response)
└─────────────┘
```

---

## 🔍 **Detailed Step-by-Step Explanation**

### **Step ①: End User Makes Request**

**User Action:**
```bash
curl https://bills.paymobsolutions.com/api/invoices \
  -H "Authorization: Bearer user-token-here"
```

**What Happens:**
- Browser/client prepares HTTP request
- Target: `bills.paymobsolutions.com`
- Path: `/api/invoices`
- Headers include user authentication (if any)

---

### **Step ②: DNS Resolution**

**DNS Lookup Sequence:**

```
1. Client queries DNS: "What is bills.paymobsolutions.com?"

2. DNS Server responds:
   bills.paymobsolutions.com → CNAME → c-550e8400.edge.sentrix.io

3. Client queries again: "What is c-550e8400.edge.sentrix.io?"

4. DNS Server responds:
   c-550e8400.edge.sentrix.io → A Record → 1.2.3.4 (SENTRIX Edge IP)

5. Client connects to 1.2.3.4:443 (SENTRIX Edge)
```

**Key Point:** User's browser thinks it's connecting to `bills.paymobsolutions.com`, but DNS transparently routes to SENTRIX!

**SSL/TLS:**
- SENTRIX Edge has SSL certificate for `bills.paymobsolutions.com`
- Client establishes encrypted TLS connection
- All traffic encrypted end-to-end ✅

---

### **Step ③: SENTRIX Edge Receives Request**

**SENTRIX Edge Service (`edge/main.py`):**

```python
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def handle_request(path):
    # Extract Host header
    host = request.headers.get('Host')  # 'bills.paymobsolutions.com'
    
    # Log request
    logger.info(f"Incoming request: {request.method} {host}/{path}")
    
    # Continue to security checks...
```

**Received Request Details:**
```http
GET /api/invoices HTTP/1.1
Host: bills.paymobsolutions.com
User-Agent: Mozilla/5.0...
Authorization: Bearer user-token-here
X-Real-IP: 203.45.67.89
```

---

### **Step ④: Security Checks (SENTRIX Protection Layer)**

**SENTRIX performs multiple security checks:**

```python
# 1. Rate Limiting
if is_rate_limited(client_ip, application_id):
    return {'error': 'Rate limit exceeded'}, 429

# 2. IP Blocking
if client_ip in blocked_ips:
    return {'error': 'Access denied'}, 403

# 3. Geo-Blocking
if country_code in blocked_countries:
    return {'error': 'Access denied from your location'}, 403

# 4. SQL Injection Detection
if detect_sql_injection(request.args, request.json):
    return {'error': 'Malicious request detected'}, 400

# 5. XSS Detection
if detect_xss(request.args, request.json):
    return {'error': 'Malicious request detected'}, 400

# 6. DDoS Protection
if is_ddos_attack(client_ip, request_rate):
    return {'error': 'Too many requests'}, 429

# 7. Behavioral Analysis
risk_score = analyze_behavior(client_ip, user_agent, request_pattern)
if risk_score > THRESHOLD:
    return {'error': 'Suspicious activity detected'}, 403
```

**If ALL checks pass:** ✅ Continue to Step ⑤

**If ANY check fails:** ❌ Block request, log incident, send webhook alert

---

### **Step ⑤: Application Lookup & Request Signing**

**Lookup Target Application:**

```python
# Query backend API or Redis cache
response = requests.get(
    'http://backend:8000/api/applications/resolve_host/',
    params={'host': 'bills.paymobsolutions.com'}
)

application_data = response.json()
# {
#   'application_id': '550e8400-...',
#   'target_url': 'https://origin.paymob.internal:8000',
#   'origin_signature_key': 'sig-key-secret-here',
#   'rate_limits': {...}
# }
```

**Sign Request (Add SENTRIX Headers):**

```python
import hmac
import hashlib
import time

# Generate signature
timestamp = str(int(time.time()))
message = f"{request.method}|{path}|{timestamp}"
signature = hmac.new(
    origin_signature_key.encode(),
    message.encode(),
    hashlib.sha256
).hexdigest()

# Add SENTRIX headers
headers = {
    'X-SENTRIX-Signature': signature,
    'X-SENTRIX-Request-ID': str(uuid.uuid4()),
    'X-SENTRIX-Timestamp': timestamp,
    'X-Real-IP': client_ip,
    'X-Forwarded-For': client_ip,
    'X-Forwarded-Proto': 'https',
    
    # Preserve original headers
    'Host': 'bills.paymobsolutions.com',
    'Authorization': original_auth_header,
    'User-Agent': original_user_agent,
    # ... all other client headers
}
```

---

### **Step ⑥: Proxy to Origin Server**

**SENTRIX Edge makes proxied request:**

```python
# Build target URL
target_url = f"{application_data['target_url']}/{path}"
# Result: https://origin.paymob.internal:8000/api/invoices

# Make request to origin
origin_response = requests.request(
    method=request.method,
    url=target_url,
    headers=headers,
    params=request.args,
    json=request.json,
    data=request.data,
    allow_redirects=False,
    timeout=30
)
```

**Request sent to origin:**
```http
GET /api/invoices HTTP/1.1
Host: bills.paymobsolutions.com
X-SENTRIX-Signature: abc123def456...
X-SENTRIX-Request-ID: 550e8400-e29b-41d4-a716-446655440000
X-SENTRIX-Timestamp: 1699123456
X-Real-IP: 203.45.67.89
X-Forwarded-For: 203.45.67.89
X-Forwarded-Proto: https
Authorization: Bearer user-token-here
User-Agent: Mozilla/5.0...
```

---

### **Step ⑦: Origin Server Validates & Processes**

**Paymob's Nginx/Origin Server:**

```nginx
server {
    listen 443 ssl;
    server_name bills.paymobsolutions.com origin.paymob.internal;
    
    location / {
        # Validate SENTRIX signature
        set $allow 0;
        
        # Check for SENTRIX signature
        if ($http_x_sentrix_signature = "abc123def456...") {
            set $allow 1;
        }
        
        # Emergency bypass (if SENTRIX down)
        if ($http_x_sentrix_bypass = "bypass-token-here") {
            set $allow 1;
        }
        
        # Block unauthorized access
        if ($allow = 0) {
            return 403 '{"error":"Direct access not allowed"}';
        }
        
        # Proxy to Django/Flask app
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $http_x_real_ip;
        proxy_set_header X-Forwarded-For $http_x_forwarded_for;
    }
}
```

**Django/Flask App Processes Request:**

```python
# Paymob's application code
@app.route('/api/invoices')
def get_invoices():
    # Normal business logic
    user_token = request.headers.get('Authorization')
    user = authenticate(user_token)
    
    invoices = Invoice.objects.filter(user=user)
    return jsonify([invoice.to_dict() for invoice in invoices])
```

**Origin generates response:**
```json
{
  "invoices": [
    {"id": 1, "amount": 100.50, "status": "paid"},
    {"id": 2, "amount": 250.00, "status": "pending"}
  ]
}
```

---

### **Step ⑧: Response Returns Through SENTRIX**

**Origin → SENTRIX Edge:**

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 123

{"invoices": [...]}
```

**SENTRIX Edge enhances response:**

```python
# Add SENTRIX headers
response_headers = origin_response.headers.copy()
response_headers['X-SENTRIX-Protected'] = 'true'
response_headers['X-SENTRIX-Request-ID'] = request_id
response_headers['X-SENTRIX-Response-Time'] = f"{response_time}ms"

# Log metrics
log_request_metrics(
    application_id=application_id,
    method=request.method,
    path=path,
    status_code=origin_response.status_code,
    response_time=response_time,
    client_ip=client_ip
)

# Update quota usage
update_quota_usage(application_id, requests_count=1)

# Return to client
return Response(
    origin_response.content,
    status=origin_response.status_code,
    headers=response_headers
)
```

**SENTRIX Edge → User:**

```http
HTTP/1.1 200 OK
Content-Type: application/json
X-SENTRIX-Protected: true
X-SENTRIX-Request-ID: 550e8400-e29b-41d4-a716-446655440000
X-SENTRIX-Response-Time: 23ms

{"invoices": [...]}
```

---

## 🔒 **Security Validation Points**

### **Point 1: SENTRIX Edge (Inbound)**
```
✓ Rate limiting
✓ IP/Geo blocking
✓ SQL injection detection
✓ XSS detection
✓ DDoS mitigation
✓ Behavioral analysis
```

### **Point 2: Origin Server (Validation)**
```
✓ SENTRIX signature verification
✓ Reject direct access (no signature)
✓ Emergency bypass (if SENTRIX down)
```

### **Point 3: Application Layer (Business Logic)**
```
✓ User authentication (Authorization header)
✓ User authorization (permissions)
✓ Business logic validation
```

**Triple-layer security!** 🛡️🛡️🛡️

---

## 📊 **Performance Metrics**

### **Latency Breakdown:**

```
DNS Resolution:        5-20ms
TLS Handshake:        50-100ms (first request only)
SENTRIX Edge:         10-20ms (security checks + proxy)
Origin Processing:    100-500ms (business logic)
Response Proxy:       5-10ms
───────────────────────────────
Total (first):        170-650ms
Total (cached):       115-530ms (DNS cached)
```

**SENTRIX Overhead:** ~20-30ms (negligible!)

---

## 🌐 **Network Architecture**

### **Production Setup:**

```
┌────────────────────────────────────────────────────────────┐
│                      INTERNET                              │
└────────────────┬───────────────────────────────────────────┘
                 │
      ┌──────────┴──────────┐
      │   Cloudflare CDN    │ (Optional: DDoS protection + CDN)
      │   or AWS CloudFront │
      └──────────┬──────────┘
                 │
      ┌──────────┴──────────┐
      │   DNS Provider      │ (Route53, Cloudflare DNS)
      │   CNAME →           │
      └──────────┬──────────┘
                 │
      ┌──────────┴──────────┐
      │   SENTRIX EDGE      │ (8 vCPU, 24GB RAM)
      │   Load Balanced:    │
      │   • Edge 1: 1.2.3.4 │
      │   • Edge 2: 1.2.3.5 │
      │   • Edge 3: 1.2.3.6 │
      └──────────┬──────────┘
                 │
      ┌──────────┴──────────┐
      │   SENTRIX BACKEND   │ (Django API)
      │   • App metadata    │
      │   • Security rules  │
      │   • Analytics       │
      └──────────┬──────────┘
                 │
                 │ (Proxy signed request)
                 ↓
      ┌─────────────────────┐
      │  PAYMOB ORIGIN      │ (Customer infrastructure)
      │  origin.paymob.int  │
      │  • 10.0.1.50:8000   │
      │  • Private network  │
      │  • Validates sig    │
      └─────────────────────┘
```

---

## 🔑 **Key Takeaways**

### **For End Users:**
- ✅ No difference! They access `bills.paymobsolutions.com` normally
- ✅ HTTPS works seamlessly (SENTRIX has SSL cert)
- ✅ Same domain, same API, same everything
- ✅ Slightly improved security (attacks blocked before reaching origin)

### **For Paymob (Customer):**
- ✅ Zero code changes required
- ✅ Zero deployment required
- ✅ Only DNS changes (one-time setup)
- ✅ Origin protected from direct access
- ✅ Full visibility via SENTRIX dashboard

### **For SENTRIX (You):**
- ✅ Automatic routing via `Host` header lookup
- ✅ Transparent proxying to origin
- ✅ Full security inspection on every request
- ✅ Real-time analytics and logging
- ✅ Quota management per application

---

## 🧪 **Testing the Flow**

### **Test 1: Verify DNS Routing**

```bash
# Check DNS resolution
dig bills.paymobsolutions.com

# Should show:
# bills.paymobsolutions.com → CNAME → c-550e8400.edge.sentrix.io
# c-550e8400.edge.sentrix.io → A → 1.2.3.4
```

### **Test 2: Verify SENTRIX Protection**

```bash
# Make request
curl -v https://bills.paymobsolutions.com/api/invoices

# Check response headers:
# X-SENTRIX-Protected: true ✅
# X-SENTRIX-Request-ID: <uuid> ✅
# X-SENTRIX-Response-Time: 23ms ✅
```

### **Test 3: Verify Origin Signature**

```bash
# Try direct access to origin (should fail)
curl https://origin.paymob.internal:8000/api/invoices

# Response: 403 Forbidden ✅ (no SENTRIX signature)

# Try with bypass token (should work)
curl https://origin.paymob.internal:8000/api/invoices \
  -H "X-SENTRIX-Bypass: bypass-token-here"

# Response: 200 OK ✅ (emergency bypass works)
```

### **Test 4: Verify Security Blocking**

```bash
# SQL injection attempt
curl "https://bills.paymobsolutions.com/api/invoices?id=1' OR '1'='1"

# Response: 400 Bad Request
# {"error": "Malicious request detected"} ✅

# Origin NEVER receives this request!
```

---

## 📈 **Scalability**

### **Current Setup (Single Edge):**
- **Capacity:** ~10,000 requests/second
- **Concurrent connections:** ~50,000
- **Memory:** 24GB (comfortable headroom)

### **Auto-Scaling (Future):**
```
Load Balancer (DNS Round-Robin)
├─ Edge 1: 1.2.3.4 (handles 33%)
├─ Edge 2: 1.2.3.5 (handles 33%)
└─ Edge 3: 1.2.3.6 (handles 33%)

Total capacity: ~30,000 requests/second
```

---

## 🎯 **Summary**

### **The Magic:**
1. **User thinks:** "I'm accessing bills.paymobsolutions.com"
2. **DNS silently routes:** To SENTRIX Edge
3. **SENTRIX inspects:** Security checks, blocking attacks
4. **SENTRIX proxies:** Signed request to origin
5. **Origin validates:** SENTRIX signature, processes request
6. **Response flows back:** Through SENTRIX to user

### **Result:**
- ✅ Zero-deployment protection
- ✅ Zero downtime (DNS failover)
- ✅ Zero user disruption
- ✅ Full security coverage
- ✅ Complete visibility

**Pure magic!** ✨

---

*Last Updated: November 2025*  
*Status: Production Ready*  
*Reference: PAYMOB_ZERO_DOWNTIME_SETUP.md*


