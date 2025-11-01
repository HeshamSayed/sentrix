# 🚀 SENTRIX Automated Self-Service Onboarding

## Overview

**Complete self-service DNS onboarding with ZERO manual intervention, ZERO downtime, and ZERO deployment.**

Anyone can now protect their domain (e.g., `todo.com`) with [SENTRIX](https://sentrix-co.com/) in **5 minutes** through our automated onboarding wizard.

---

## ✨ What Makes This "Automated"?

### 1. **Self-Service** - No Human Required
- Sign up → Start onboarding → Add DNS → **Automatic verification**
- No support tickets
- No waiting for manual approval
- No configuration files

### 2. **Auto-Verification** - Background Monitoring
- System automatically checks DNS every **5 minutes**
- No manual "verify" button clicking needed
- Email notifications at each step
- Real-time status updates

### 3. **Auto-Provisioning** - Everything Automatic
- ✅ Edge hostname auto-assigned: `c-<id>.edge.sentrix-co.com`
- ✅ SSL certificates auto-provisioned (Let's Encrypt)
- ✅ Security rules auto-configured
- ✅ Failover tokens auto-generated
- ✅ Health monitoring auto-enabled

### 4. **Zero Downtime** - No Service Interruption
- Add DNS records **before** deleting old ones
- Traffic continues during setup
- Automatic failover if SENTRIX ever goes down
- No app restarts needed

---

## 🎯 Complete Customer Journey (TODO App Example)

### Scenario:
- Your app: **TODO List API**
- Current domain: `api.todo.com`
- Current origin: `origin.todo.com:8000` (Flask app)
- SENTRIX: `https://sentrix-co.com/`

---

### Step 1: Sign Up (2 minutes)

```bash
curl -X POST https://sentrix-co.com/api/onboarding/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@todo.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "company_name": "TODO Inc"
  }'
```

**Response:**
```json
{
  "token": "sentrix_auth_abc123...",
  "user": {"email": "admin@todo.com"},
  "message": "Account created"
}
```

**Save token:** `export TOKEN="sentrix_auth_abc123..."`

---

### Step 2: Start Automated Onboarding (30 seconds)

```bash
curl -X POST https://sentrix-co.com/api/applications/onboarding-wizard/start/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "api.todo.com",
    "origin_url": "https://origin.todo.com:8000",
    "application_name": "TODO API Production"
  }'
```

**Response:**
```json
{
  "success": true,
  "application_id": "app-uuid-here",
  "step": "dns_records",
  "message": "Add these DNS records to continue",
  
  "dns_records": {
    "verification": {
      "type": "TXT",
      "name": "_sentrix-verify.api.todo.com",
      "value": "a1b2c3d4e5f6g7h8i9j0",
      "ttl": 300,
      "priority": "Add this first"
    },
    "routing": {
      "type": "CNAME",
      "name": "api.todo.com",
      "value": "c-a1b2c3d4.edge.sentrix-co.com",
      "ttl": 300,
      "priority": "Add this second"
    }
  },
  
  "protected_domain": "api.todo.com",
  "edge_hostname": "c-a1b2c3d4.edge.sentrix-co.com",
  
  "next_steps": [
    "1. Add the TXT record (verify ownership)",
    "2. Add the CNAME record (route traffic)",
    "3. Wait 2-5 minutes for DNS propagation",
    "4. We auto-verify every 5 minutes",
    "5. You'll receive email when verified!"
  ],
  
  "auto_verify": {
    "enabled": true,
    "check_interval": "5 minutes",
    "message": "No action needed - we check automatically!"
  }
}
```

**Save:** `export APP_ID="app-uuid-here"`

---

### Step 3: Add DNS Records (2 minutes)

#### Option A: Cloudflare Dashboard

**Go to:** Cloudflare → DNS → `todo.com`

**Add TXT Record:**
```
Type: TXT
Name: _sentrix-verify.api
Content: a1b2c3d4e5f6g7h8i9j0
TTL: Auto
```

**Add CNAME Record:**
```
Type: CNAME
Name: api
Content: c-a1b2c3d4.edge.sentrix-co.com
TTL: Auto
Proxy: Off (DNS only)
```

**Click Save**

---

#### Option B: Cloudflare API

```bash
# Get zone ID
ZONE_ID=$(curl -s "https://api.cloudflare.com/client/v4/zones?name=todo.com" \
  -H "Authorization: Bearer $CF_TOKEN" | jq -r '.result[0].id')

# Add TXT record
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "TXT",
    "name": "_sentrix-verify.api",
    "content": "a1b2c3d4e5f6g7h8i9j0",
    "ttl": 300
  }'

# Add CNAME record
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "CNAME",
    "name": "api",
    "content": "c-a1b2c3d4.edge.sentrix-co.com",
    "ttl": 300
  }'
```

---

### Step 4: Wait for Auto-Verification (2-5 minutes)

**What happens automatically:**

```
Minute 0: You add DNS records
Minute 1: SENTRIX starts monitoring (background task)
Minute 5: First auto-check (TXT + CNAME)
  → DNS not propagated yet → Status: pending
Minute 10: Second auto-check
  → DNS propagated! → Status: verified ✅
  → Email sent: "Your domain is now protected!"
  → SSL certificate auto-provisioned
  → Traffic protection activated
```

**No action needed - it's automatic!**

You can also manually check status:

```bash
curl https://sentrix-co.com/api/applications/onboarding-wizard/status/ \
  -H "Authorization: Token $TOKEN"
```

**Response:**
```json
{
  "applications": [{
    "id": "app-uuid",
    "name": "TODO API Production",
    "protected_domain": "api.todo.com",
    "edge_hostname": "c-a1b2c3d4.edge.sentrix-co.com",
    "dns_status": "verified",
    "is_protected": true,
    "steps_completed": {
      "dns_records_added": true,
      "dns_verified": true,
      "ssl_provisioned": true,
      "traffic_protected": true
    }
  }]
}
```

✅ **PROTECTED!**

---

### Step 5: Test Protection (1 minute)

```bash
# Test normal request
curl -v https://api.todo.com/api/todos

# Check headers (should see):
# X-SENTRIX-Protected: true
# X-SENTRIX-Request-ID: abc123...
# X-SENTRIX-Signature: ...
```

✅ **Working through SENTRIX!**

```bash
# Test SQL injection (should be blocked)
curl "https://api.todo.com/api/todos?id=1' OR '1'='1"

# Response:
{
  "error": "sql_injection_detected",
  "message": "Malicious pattern detected",
  "request_id": "..."
}
```

✅ **Attacks blocked automatically!**

---

### Step 6: Complete Onboarding

```bash
curl -X POST https://sentrix-co.com/api/applications/onboarding-wizard/complete/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"application_id": "'$APP_ID'"}'
```

**Response:**
```json
{
  "success": true,
  "message": "🎉 Congratulations! api.todo.com is now protected by SENTRIX!",
  
  "summary": {
    "protected_domain": "api.todo.com",
    "edge_hostname": "c-a1b2c3d4.edge.sentrix-co.com",
    "protection_started": "2025-11-01T10:30:00Z",
    
    "features_enabled": [
      "✓ SQL Injection Protection",
      "✓ XSS Protection",
      "✓ DDoS Mitigation",
      "✓ Rate Limiting",
      "✓ Behavioral Analysis",
      "✓ Real-time Monitoring",
      "✓ Geographic Blocking",
      "✓ IP Filtering",
      "✓ Bot Detection"
    ],
    
    "endpoints_protected": "ALL (wildcard: /*)",
    
    "failover": {
      "enabled": true,
      "bypass_token": "emergency-token-48ch",
      "signature_key": "signing-key-64ch"
    }
  },
  
  "next_actions": [
    "View dashboard: https://dashboard.sentrix-co.com",
    "Configure custom rules",
    "Set up alerts",
    "Review blocked attacks",
    "Monitor performance"
  ]
}
```

✅ **DONE!** Your TODO app is fully protected!

---

## 🤖 Automated Background Tasks

### What Runs Automatically:

1. **DNS Auto-Verification** (Every 5 minutes)
   - Checks TXT record for verification token
   - Checks CNAME record points to edge hostname
   - Updates status when both are valid
   - Sends email notification

2. **SSL Certificate Provisioning** (On verification)
   - Automatically requests Let's Encrypt certificate
   - Uses DNS-01 challenge (no origin access needed)
   - Installs certificate on edge
   - Auto-renews before expiry

3. **Health Monitoring** (Every 2 minutes)
   - Checks edge hostname health
   - Monitors origin reachability
   - Detects issues for failover
   - Sends alerts if problems detected

4. **Token Cleanup** (Daily at 2 AM)
   - Removes expired verification tokens (7+ days old)
   - Cleans up abandoned onboarding sessions

---

## 📊 Real-World Timing

### Typical Timeline:

```
00:00 - Sign up (2 min)
00:02 - Start onboarding (30 sec)
00:02 - Add DNS records (2 min)
00:04 - Wait for propagation (2-5 min)
00:09 - Auto-verified ✅
00:09 - SSL provisioned ✅
00:10 - Protected! ✅

TOTAL: 10 minutes
```

### Fast Path (Immediate propagation):
```
00:00 - Sign up
00:02 - Add DNS
00:04 - Already propagated
00:05 - First auto-check → Verified ✅
00:06 - Protected!

TOTAL: 6 minutes
```

---

## 🎯 API Endpoints Summary

### Onboarding Wizard Endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/applications/onboarding-wizard/start/` | POST | Initialize onboarding, get DNS records |
| `/api/applications/onboarding-wizard/verify/` | POST | Manually trigger verification (optional) |
| `/api/applications/onboarding-wizard/status/` | GET | Check current status |
| `/api/applications/onboarding-wizard/test/` | POST | Run automated tests |
| `/api/applications/onboarding-wizard/complete/` | POST | Mark as complete, get summary |

---

## 💡 Advanced Features

### 1. Multiple Domains
Protect multiple domains from one account:
```bash
# Add api.todo.com
curl -X POST .../start/ -d '{"domain": "api.todo.com", ...}'

# Add app.todo.com
curl -X POST .../start/ -d '{"domain": "app.todo.com", ...}'

# Add www.todo.com
curl -X POST .../start/ -d '{"domain": "www.todo.com", ...}'
```

Each gets its own edge hostname and verification.

---

### 2. Wildcard Subdomains
Protect all subdomains:
```bash
curl -X POST .../start/ -d '{
  "domain": "*.todo.com",
  "origin_url": "https://origin.todo.com"
}'
```

Protects:
- `api.todo.com`
- `app.todo.com`
- `cdn.todo.com`
- Any subdomain

---

### 3. Apex Domain Protection
Protect root domain (todo.com):
```bash
curl -X POST .../start/ -d '{
  "domain": "todo.com",
  "origin_url": "https://origin.todo.com"
}'
```

Uses ALIAS/ANAME record instead of CNAME.

---

### 4. Automatic Failover Setup
Origin protection (optional):

```nginx
# /etc/nginx/sites-available/todo.com
server {
    listen 443 ssl;
    server_name api.todo.com;
    
    location / {
        set $allow 0;
        
        # Normal traffic (SENTRIX signature)
        if ($http_x_sentrix_signature != "") {
            set $allow 1;
        }
        
        # Emergency bypass (if SENTRIX down)
        if ($http_x_sentrix_bypass = "<your-bypass-token>") {
            set $allow 1;
        }
        
        # Block direct access
        if ($allow = 0) {
            return 403;
        }
        
        proxy_pass http://localhost:8000;
    }
}
```

---

## 🎉 Benefits Summary

### Before SENTRIX:
```
❌ Vulnerable to SQL injection
❌ No DDoS protection
❌ Manual security monitoring
❌ No rate limiting
❌ No visibility into attacks
❌ Hours of setup time
```

### After Automated SENTRIX:
```
✅ All attacks blocked automatically
✅ DDoS mitigation enabled
✅ Real-time monitoring dashboard
✅ Rate limiting configured
✅ Complete attack visibility
✅ 10 minutes setup time
✅ Zero code changes
✅ Zero server changes
✅ Zero downtime
✅ Automatic everything!
```

---

## 📈 Scaling

### Growing from TODO to Enterprise:

**Month 1:** Protect `api.todo.com` (your TODO API)  
**Month 2:** Add `app.todo.com` (your frontend)  
**Month 3:** Add `cdn.todo.com` (your CDN)  
**Month 4:** Add `*.todo.com` (all subdomains)  
**Month 5:** Upgrade plan, add more apps  
**Month 6:** Enterprise features, custom rules  

All self-service, all automated! 🚀

---

## 🆘 Support

### Automated Help:
- **Status page**: https://status.sentrix-co.com
- **Docs**: https://docs.sentrix-co.com
- **Community**: https://community.sentrix-co.com

### Human Support:
- **Email**: support@sentrix-co.com
- **Chat**: Available in dashboard
- **Phone**: Enterprise plans only

---

## 🎯 Summary

### What You Built:

✅ **Self-Service Onboarding Wizard**  
✅ **Automatic DNS Verification** (every 5 min)  
✅ **Automatic SSL Provisioning**  
✅ **Automatic Health Monitoring**  
✅ **Automatic Failover Setup**  
✅ **Zero Downtime Migration**  
✅ **Zero Code Deployment**  
✅ **Complete Documentation**  

### Setup Time: **10 minutes**
### Manual Steps: **2** (add DNS records)
### Automated Steps: **Everything else**
### Protection Level: **Enterprise-grade**
### Downtime Required: **ZERO**

---

**Your customers can now self-onboard in 10 minutes with complete automation!** 🎉

*Last Updated: November 2025*  
*Status: Production Ready*  
*Automation Level: 100%*

