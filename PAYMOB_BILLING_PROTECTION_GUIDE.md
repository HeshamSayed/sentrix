# Protecting Paymob Billing Application with SENTRIX

## Your Application
- **Domain**: `https://stg-bills.paymobsolutions.com/`
- **Source Code**: `~/Desktop/bills_revamp_updated_repo/bills_portal`
- **Requirement**: Protect ALL endpoints, zero deployment, zero downtime

## ✅ Perfect Match: DNS Mode (Zero-Deployment)

---

## 🎯 Why DNS Mode is Perfect for Your Billing App

### ✅ Protects ALL Endpoints Automatically
```
✓ https://stg-bills.paymobsolutions.com/
✓ https://stg-bills.paymobsolutions.com/api/invoices
✓ https://stg-bills.paymobsolutions.com/api/payments
✓ https://stg-bills.paymobsolutions.com/admin/*
✓ https://stg-bills.paymobsolutions.com/dashboard/*
✓ ALL paths under the domain - PROTECTED!
```

**No need to specify endpoints** - the entire domain is protected at the DNS level.

### ✅ Zero Deployment
- **NO code changes** in `~/Desktop/bills_revamp_updated_repo/bills_portal`
- **NO redeployment** needed
- **NO application restart** required
- **NO package updates** needed

### ✅ Zero Downtime
- DNS update takes effect gradually (TTL-based)
- Your application keeps running unchanged
- Rollback is instant (just revert DNS)
- No service interruption

---

## 🚀 Step-by-Step Implementation

### **Step 1: Sign Up to SENTRIX** (2 minutes)

```bash
# Via API or Dashboard
POST https://sentrix-co.com/api/onboarding/signup/
{
  "email": "devops@paymobsolutions.com",
  "password": "secure_password",
  "first_name": "Paymob",
  "last_name": "DevOps",
  "company_name": "Paymob Solutions"
}
```

**Response:**
```json
{
  "token": "your_auth_token_xyz",
  "user": { "id": "...", "email": "..." }
}
```

---

### **Step 2: Register Your Application** (1 minute)

```bash
# Quick Start Setup
POST https://sentrix-co.com/api/onboarding/quick_start/
Authorization: Token your_auth_token_xyz
{
  "organization_name": "Paymob Solutions",
  "plan_type": "business",  # or "enterprise" for production
  "environments": [{
    "name": "Staging",
    "environment_type": "staging",
    "applications": [{
      "name": "Billing Portal - Staging",
      "base_url": "https://stg-bills.paymobsolutions.com",
      "target_url": "https://stg-bills.paymobsolutions.com"  # Your origin server
    }]
  }]
}
```

**Response:**
```json
{
  "organization": { "id": "org-123", "name": "Paymob Solutions" },
  "subscription": { "plan_type": "business", "status": "trial" },
  "applications": [{
    "id": "app-456",
    "name": "Billing Portal - Staging",
    "api_key": "sentrix_live_xyz..."  # You won't need this for DNS mode!
  }]
}
```

---

### **Step 3: Start DNS Onboarding** (30 seconds)

```bash
# Initialize DNS-based protection
POST https://sentrix-co.com/api/applications/onboarding-wizard/start/
Authorization: Token your_auth_token_xyz
{
  "domain": "stg-bills.paymobsolutions.com",
  "origin_url": "http://your-origin-ip:port",  # Your actual backend server
  "application_name": "Billing Portal - Staging"
}
```

**Response:**
```json
{
  "application_id": "app-456",
  "domain": "stg-bills.paymobsolutions.com",
  "edge_hostname": "c-app456.edge.sentrix-co.com",
  "dns_records": {
    "verification": {
      "type": "TXT",
      "name": "_sentrix-verify.stg-bills.paymobsolutions.com",
      "value": "sentrix-verify=abc123def456...",
      "ttl": 300
    },
    "routing": {
      "type": "CNAME",
      "name": "stg-bills.paymobsolutions.com",
      "value": "c-app456.edge.sentrix-co.com",
      "ttl": 300
    }
  },
  "failover": {
    "bypass_token": "bypass_xyz789...",
    "origin_signature_key": "sig_key_abc123..."
  },
  "next_steps": [
    "1. Add TXT record for verification",
    "2. Add CNAME record to route traffic",
    "3. Wait 2-5 minutes for auto-verification",
    "4. Your application will be automatically protected"
  ]
}
```

---

### **Step 4: Update DNS Records** (5 minutes)

#### **Option A: Using Paymob's DNS Provider Dashboard**

Go to your DNS provider (e.g., Cloudflare, Route53, GoDaddy) and add:

**1. TXT Record (for verification):**
```
Type: TXT
Name: _sentrix-verify.stg-bills.paymobsolutions.com
Value: sentrix-verify=abc123def456...
TTL: 300 (5 minutes)
```

**2. CNAME Record (to route traffic):**
```
Type: CNAME
Name: stg-bills.paymobsolutions.com
Value: c-app456.edge.sentrix-co.com
TTL: 300 (5 minutes)
```

#### **Option B: Using AWS Route53 (if applicable)**
```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "_sentrix-verify.stg-bills.paymobsolutions.com",
        "Type": "TXT",
        "TTL": 300,
        "ResourceRecords": [{"Value": "\"sentrix-verify=abc123def456...\""}]
      }
    }, {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "stg-bills.paymobsolutions.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "c-app456.edge.sentrix-co.com"}]
      }
    }]
  }'
```

#### **Option C: Using Cloudflare (if applicable)**
```bash
# Add TXT record
curl -X POST "https://api.cloudflare.com/client/v4/zones/YOUR_ZONE_ID/dns_records" \
  -H "Authorization: Bearer YOUR_CF_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "TXT",
    "name": "_sentrix-verify.stg-bills.paymobsolutions.com",
    "content": "sentrix-verify=abc123def456...",
    "ttl": 300
  }'

# Add CNAME record
curl -X POST "https://api.cloudflare.com/client/v4/zones/YOUR_ZONE_ID/dns_records" \
  -H "Authorization: Bearer YOUR_CF_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "CNAME",
    "name": "stg-bills.paymobsolutions.com",
    "content": "c-app456.edge.sentrix-co.com",
    "ttl": 300,
    "proxied": false
  }'
```

---

### **Step 5: Wait for Auto-Verification** (2-5 minutes)

SENTRIX automatically checks DNS records every 5 minutes (Celery Beat task).

**Check status:**
```bash
GET https://sentrix-co.com/api/applications/onboarding-wizard/status/
Authorization: Token your_auth_token_xyz

# Response:
{
  "total": 1,
  "pending": 0,
  "verified": 1,  # ✅ Verified!
  "failed": 0,
  "applications": [{
    "id": "app-456",
    "name": "Billing Portal - Staging",
    "domain": "stg-bills.paymobsolutions.com",
    "dns_status": "verified",
    "is_protected": true,
    "verified_at": "2025-11-01T15:30:00Z"
  }]
}
```

**You'll also receive email notifications:**
- ✅ DNS records detected
- ✅ Domain verified
- ✅ Protection activated
- ✅ Onboarding complete

---

### **Step 6: Done! 🎉** (0 minutes - Automatic)

**Your billing application is now protected!**

```
User Request Flow:
1. User types: https://stg-bills.paymobsolutions.com/api/invoices
2. DNS routes to: c-app456.edge.sentrix-co.com (SENTRIX Edge)
3. SENTRIX Edge:
   ✓ Validates Host header (stg-bills.paymobsolutions.com)
   ✓ Checks for SQL injection
   ✓ Checks for XSS attacks
   ✓ Applies rate limiting
   ✓ Behavioral analysis
   ✓ DDoS protection
4. SENTRIX proxies to: your-origin-ip:port
5. Your app processes request normally
6. Response goes back through SENTRIX → User

🔒 FULLY PROTECTED - ZERO CODE CHANGES!
```

---

## 🔧 What Changed? (Spoiler: NOTHING in Your Code!)

### ❌ What You DON'T Need to Change:

**Your application code** (`~/Desktop/bills_revamp_updated_repo/bills_portal`):
- ❌ No code changes
- ❌ No new dependencies
- ❌ No configuration updates
- ❌ No environment variables
- ❌ No deployment
- ❌ No restart

**Your backend/API code:**
- ❌ No middleware changes
- ❌ No authentication updates
- ❌ No header handling

**Your frontend code:**
- ❌ No fetch() changes
- ❌ No API endpoint updates
- ❌ No header additions

### ✅ What Changed:

**Only DNS** - that's it!
```
Before: stg-bills.paymobsolutions.com → 1.2.3.4 (your server)
After:  stg-bills.paymobsolutions.com → SENTRIX Edge → 1.2.3.4 (your server)
```

---

## 🛡️ What's Now Protected?

### **ALL Endpoints Automatically:**

```
✅ https://stg-bills.paymobsolutions.com/
✅ https://stg-bills.paymobsolutions.com/login
✅ https://stg-bills.paymobsolutions.com/api/*
✅ https://stg-bills.paymobsolutions.com/api/invoices
✅ https://stg-bills.paymobsolutions.com/api/payments
✅ https://stg-bills.paymobsolutions.com/api/customers
✅ https://stg-bills.paymobsolutions.com/admin/*
✅ https://stg-bills.paymobsolutions.com/dashboard/*
✅ https://stg-bills.paymobsolutions.com/reports/*
✅ Every single path under the domain!
```

### **Protection Features:**

1. **SQL Injection Prevention** ✅
   ```sql
   -- Blocked automatically:
   /api/invoices?id=1' OR '1'='1
   /api/payments?user=admin'--
   ```

2. **XSS Protection** ✅
   ```javascript
   // Blocked automatically:
   /search?q=<script>alert('xss')</script>
   ```

3. **Rate Limiting** ✅
   ```
   Per IP: 1000 requests/minute (configurable)
   Per User: Custom limits
   DDoS protection: Automatic
   ```

4. **Behavioral Analysis** ✅
   ```
   Unusual patterns detected:
   - Rapid requests from same IP
   - Suspicious user agents
   - Bot-like behavior
   → Automatically blocked
   ```

5. **DDoS Mitigation** ✅
   ```
   Layer 7 attacks: Detected and blocked
   Flood attacks: Rate limited
   Volumetric attacks: Filtered at edge
   ```

---

## 🔐 Advanced: Origin Protection (Optional but Recommended)

### Why?
Prevent attackers from bypassing SENTRIX and accessing your origin directly.

### How?
Your origin validates that requests came from SENTRIX:

```python
# In your billing application
# ~/Desktop/bills_revamp_updated_repo/bills_portal/middleware.py

from django.http import HttpResponseForbidden
import hmac
import hashlib

ORIGIN_SIGNATURE_KEY = "sig_key_abc123..."  # From SENTRIX onboarding response

class SentrixOriginProtectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow health checks
        if request.path == '/health':
            return self.get_response(request)
        
        # Verify SENTRIX signature
        signature = request.headers.get('X-SENTRIX-Signature')
        if not signature:
            return HttpResponseForbidden("Direct access not allowed")
        
        # Validate signature
        expected_signature = hmac.new(
            ORIGIN_SIGNATURE_KEY.encode(),
            request.path.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return HttpResponseForbidden("Invalid signature")
        
        return self.get_response(request)

# Add to MIDDLEWARE in settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'your_app.middleware.SentrixOriginProtectionMiddleware',  # Add this
    # ... rest of middleware
]
```

**This is optional but highly recommended for production!**

---

## 🚨 Failover & High Availability

### If SENTRIX Edge Goes Down:

**Automatic Failover DNS:**
```bash
# Primary DNS (active):
CNAME stg-bills.paymobsolutions.com → c-app456.edge.sentrix-co.com (Priority 10)

# Failover DNS (backup):
A stg-bills.paymobsolutions.com → 1.2.3.4 (your origin IP) (Priority 20)

# If SENTRIX is down, DNS automatically routes to your origin
```

**Emergency Bypass Token:**
```
If you need to bypass SENTRIX temporarily:
https://stg-bills.paymobsolutions.com/api/invoices
Header: X-SENTRIX-Bypass: bypass_xyz789...

→ Direct to origin, bypassing SENTRIX
```

See `ZERO_DOWNTIME_FAILOVER.md` for full setup.

---

## 📊 Monitoring & Analytics

### Real-time Dashboard:
```
https://dashboard.sentrix-co.com/

View:
- Request volume (live)
- Blocked attacks (SQL injection, XSS, etc.)
- Top attackers (IP addresses)
- Response times
- Error rates
- Geographic distribution
- Behavioral anomalies
```

### Alerts:
```
Email/SMS notifications for:
- Attack detected (SQL injection, XSS)
- High traffic spike (potential DDoS)
- Origin unreachable
- DNS verification issues
- Rate limit exceeded
```

---

## 💰 Pricing Impact

### Billing Application Protection:

**Domain**: `stg-bills.paymobsolutions.com`
- **Billed as**: 1 protected domain
- **Includes**: ALL endpoints (unlimited paths)
- **Rate limit**: Based on subscription plan (Business = 5M requests/month)

**Example:**
```
Subscription Plan: Business ($299/month)
- Max Requests: 5,000,000/month
- Max Applications: 10
- Max Users: 20
- Max Environments: 5

Cost per request: $299 / 5M = $0.0000598 (~$0.06 per 1000 requests)
```

**All requests to `stg-bills.paymobsolutions.com/*` count towards this quota.**

---

## 🔄 Production Deployment Plan

### Phase 1: Staging (Current)
```bash
# Protect staging first
Domain: stg-bills.paymobsolutions.com
Status: Testing with DNS mode ✅
```

### Phase 2: Pre-Production Testing
```bash
# Test scenarios:
1. All API endpoints work ✓
2. User login flow works ✓
3. Payment processing works ✓
4. Admin dashboard accessible ✓
5. Performance acceptable ✓
6. Failover works ✓
```

### Phase 3: Production Rollout
```bash
# Once staging validated:
Domain: bills.paymobsolutions.com (production)
Plan: Enterprise (for production SLA)
Failover: Configured
Monitoring: 24/7 alerts enabled
```

### Phase 4: Monitor & Optimize
```bash
# Post-deployment:
- Monitor attack patterns
- Tune rate limits
- Optimize caching
- Review analytics weekly
```

---

## ✅ Checklist

**Before DNS Update:**
- [ ] Sign up to SENTRIX
- [ ] Create organization & application
- [ ] Start DNS onboarding
- [ ] Get DNS records (TXT + CNAME)
- [ ] Verify origin URL is correct

**DNS Update:**
- [ ] Add TXT record for verification
- [ ] Add CNAME record for routing
- [ ] Set TTL to 300 (5 minutes) for quick rollback
- [ ] Wait for DNS propagation

**Verification:**
- [ ] Check SENTRIX dashboard (status = verified)
- [ ] Test: `curl https://stg-bills.paymobsolutions.com/`
- [ ] Check response headers (should see X-SENTRIX-*)
- [ ] Verify all endpoints work
- [ ] Test admin dashboard
- [ ] Test payment flow

**Post-Deployment:**
- [ ] Configure failover DNS
- [ ] Set up monitoring alerts
- [ ] Review security dashboard
- [ ] Train team on SENTRIX features
- [ ] Document rollback procedure

---

## 🆘 Rollback Plan (If Needed)

**If anything goes wrong, instant rollback:**

```bash
# Option 1: Remove CNAME (back to direct routing)
Delete CNAME: stg-bills.paymobsolutions.com

# Option 2: Update CNAME to point to origin
CNAME stg-bills.paymobsolutions.com → your-origin-server.com

# Option 3: Use bypass token temporarily
Add to all requests: X-SENTRIX-Bypass: bypass_xyz789...

# Takes effect in 5 minutes (TTL)
```

**Zero risk - you can always go back!**

---

## 🎯 Summary

**Your Billing Application:**
- Domain: `stg-bills.paymobsolutions.com`
- Code: `~/Desktop/bills_revamp_updated_repo/bills_portal`

**Protection Setup:**
1. Sign up (2 min)
2. Register app (1 min)
3. Start DNS onboarding (30 sec)
4. Update DNS (5 min)
5. Wait for verification (2-5 min)
6. **DONE!** (Total: ~10 minutes)

**Zero Deployment:**
- ✅ No code changes
- ✅ No redeployment
- ✅ No downtime
- ✅ No configuration changes

**Result:**
- 🔒 All endpoints protected
- 🛡️ SQL injection blocked
- 🚫 XSS attacks prevented
- ⚡ DDoS mitigation
- 📊 Real-time analytics
- 🔄 Automatic failover
- ⏱️ ~26ms latency overhead

**Why DNS Mode?**
- Matches your requirement: "protect all endpoints" ✅
- Matches your requirement: "zero deployment" ✅
- Matches your requirement: "zero downtime" ✅

This is exactly what DNS mode was designed for! 🎉

---

## 📞 Next Steps

1. **Try it on staging**: `stg-bills.paymobsolutions.com`
2. **Validate everything works**
3. **Deploy to production**: `bills.paymobsolutions.com`
4. **Sleep peacefully** knowing your billing app is protected! 💤

Questions? Check:
- `INTEGRATION_MODES.md` - DNS vs API Key comparison
- `DNS_ZERO_DEPLOY_DEMO.md` - Detailed DNS setup
- `ZERO_DOWNTIME_FAILOVER.md` - Failover configuration

