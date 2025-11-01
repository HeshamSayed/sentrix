# 🚀 SENTRIX Customer Journey - Complete Guide

## Overview

This guide shows exactly how clients use SENTRIX from signup to daily operations.

---

## 📋 PHASE 1: SIGN UP & ONBOARDING (2 minutes)

### Step 1: Visit SENTRIX Website
Customer goes to: `https://sentrix.io` (your domain)

### Step 2: Create Account
**Endpoint**: `POST /api/onboarding/signup/`

```bash
# Customer fills registration form
curl -X POST https://sentrix.io/api/onboarding/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@acmeapp.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "company_name": "Acme App Inc"
  }'
```

**Response**:
```json
{
  "message": "Account created successfully",
  "user": {
    "id": "user-uuid",
    "email": "john@acmeapp.com"
  },
  "token": "auth-token-here",
  "onboarding_session_id": "session-uuid"
}
```

✅ **Customer gets authentication token**

---

### Step 3: Choose Subscription Plan
Customer views available plans on website

**Plans Displayed**:
- 💎 **Free**: $0/mo - Testing (10K requests)
- 🚀 **Startup**: $149/mo - Growing (1M requests)
- 💼 **Business**: $399/mo - Scaling (10M requests)
- 🏢 **Enterprise**: $1,499/mo - Large scale (100M requests)

Each shows:
- Monthly price
- Annual price with discount
- Request quota
- Features included
- Free trial info (14 days for paid plans)

---

### Step 4: Quick Start Setup
**Endpoint**: `POST /api/onboarding/quick_start/`

Customer provides:
- Selected plan (e.g., "Startup")
- Environments needed
- Applications to protect

```json
{
  "organization_name": "Acme App Inc",
  "plan_type": "starter",
  "environments": [
    {
      "name": "Production",
      "environment_type": "production",
      "applications": [
        {
          "name": "Acme API Server",
          "base_url": "https://acmeapp.com",
          "target_url": "https://api.acmeapp.com"
        }
      ]
    }
  ]
}
```

**Response - Customer Gets**:
```json
{
  "message": "Setup completed successfully!",
  "organization": {
    "id": "org-uuid",
    "name": "Acme App Inc"
  },
  "subscription": {
    "plan_type": "starter",
    "status": "trial",
    "trial_end_date": "2025-11-15",
    "max_requests": 1000000
  },
  "environments": [...],
  "applications": [
    {
      "id": "app-uuid",
      "name": "Acme API Server",
      "api_key": "sentrix_live_Abc123Def456Ghi789Jkl012",
      "base_url": "https://acmeapp.com",
      "target_url": "https://api.acmeapp.com"
    }
  ],
  "next_steps": [
    "1. Save your API key securely",
    "2. Update your application code",
    "3. Test integration",
    "4. Monitor dashboard"
  ]
}
```

✅ **Customer receives unique API key for their application**

---

## 🔧 PHASE 2: INTEGRATION (5-10 minutes)

### Customer's Current Setup (BEFORE SENTRIX):
```
Client App → api.acmeapp.com/api/endpoint
```

### Customer's New Setup (AFTER SENTRIX):
```
Client App → edge.sentrix.io/api/endpoint
            (with X-SENTRIX-Key header)
            ↓
      SENTRIX Edge (Security Check)
            ↓
      api.acmeapp.com/api/endpoint
```

---

### Integration Steps for Customer:

#### Option A: Frontend/Mobile App Changes

**BEFORE SENTRIX**:
```javascript
// Old code
const response = await fetch('https://api.acmeapp.com/api/users', {
  headers: {
    'Authorization': 'Bearer user-token'
  }
});
```

**AFTER SENTRIX** (2 simple changes):
```javascript
// New code - Only 2 changes!
const response = await fetch('https://edge.sentrix.io/api/users', {
  //                          ^^^^^^^^^^^^^^^^^^^^^ Change 1: New endpoint
  headers: {
    'X-SENTRIX-Key': 'sentrix_live_Abc123Def456Ghi789Jkl012',
    //               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Change 2: Add API key
    'Authorization': 'Bearer user-token'  // Keep existing headers
  }
});
```

---

#### Option B: Environment Variable (Recommended)

**Step 1**: Add to `.env` file:
```bash
SENTRIX_ENABLED=true
SENTRIX_API_KEY=sentrix_live_Abc123Def456Ghi789Jkl012
SENTRIX_EDGE_URL=https://edge.sentrix.io
API_BASE_URL=https://api.acmeapp.com
```

**Step 2**: Update code once:
```javascript
const API_URL = process.env.SENTRIX_ENABLED 
  ? process.env.SENTRIX_EDGE_URL 
  : process.env.API_BASE_URL;

const headers = {
  'Authorization': 'Bearer user-token'
};

if (process.env.SENTRIX_ENABLED) {
  headers['X-SENTRIX-Key'] = process.env.SENTRIX_API_KEY;
}

const response = await fetch(`${API_URL}/api/users`, { headers });
```

✅ **Easy to enable/disable SENTRIX**  
✅ **No code changes needed to switch**  
✅ **Secure API key storage**

---

#### Option C: Reverse Proxy (Enterprise)

For customers who don't want to change client code:

**Customer's nginx config**:
```nginx
# Internal backend (not exposed)
upstream backend {
  server api.acmeapp.com:8000;
}

# Public endpoint
server {
  listen 443 ssl;
  server_name api.acmeapp.com;

  location / {
    # Forward all requests to SENTRIX Edge
    proxy_pass https://edge.sentrix.io;
    
    # Add SENTRIX API key
    proxy_set_header X-SENTRIX-Key "sentrix_live_Abc123Def456Ghi789Jkl012";
    
    # Forward original headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }
}
```

✅ **Zero client-side changes**  
✅ **Transparent to end users**  
✅ **Ideal for mobile apps (no app update needed)**

---

## 🧪 PHASE 3: TESTING (5 minutes)

### Test 1: Verify API Key Works

```bash
# Test endpoint through SENTRIX
curl https://edge.sentrix.io/api/health \
  -H "X-SENTRIX-Key: sentrix_live_Abc123Def456Ghi789Jkl012"
```

**Expected Response**:
```json
{
  "status": "ok",
  "protected_by": "SENTRIX",
  "application": "Acme API Server",
  "organization": "Acme App Inc"
}
```

✅ **API key is valid and working**

---

### Test 2: Make Real Request

```bash
# Get users through SENTRIX
curl https://edge.sentrix.io/api/users \
  -H "X-SENTRIX-Key: sentrix_live_Abc123Def456Ghi789Jkl012" \
  -H "Authorization: Bearer user-token"
```

**What Happens Behind the Scenes**:
```
1. SENTRIX Edge receives request
2. Validates API key → ✓ Valid
3. Checks rate limits → ✓ Under limit
4. Scans for threats → ✓ No threats detected
5. Proxies to api.acmeapp.com/api/users
6. Returns response to client
7. Logs request for analytics
```

✅ **Request flows through SENTRIX successfully**

---

### Test 3: Verify Security (Optional)

```bash
# Try SQL injection - SENTRIX should detect
curl "https://edge.sentrix.io/api/users?id=1' OR '1'='1" \
  -H "X-SENTRIX-Key: sentrix_live_Abc123Def456Ghi789Jkl012"
```

**Expected**: SENTRIX blocks or flags the request

✅ **Security protection is active**

---

## 📊 PHASE 4: DAILY USAGE

### Customer's Dashboard

Customer logs in to: `https://dashboard.sentrix.io`

**Dashboard Shows**:

#### 1. Overview
```
┌─────────────────────────────────────────────────┐
│ Today's Requests: 45,234 / 33,333 daily limit  │
│ This Month: 856,234 / 1,000,000                 │
│ Status: ✓ Healthy (85.6% quota remaining)      │
└─────────────────────────────────────────────────┘
```

#### 2. Real-Time Activity
```
Recent Requests:
─────────────────────────────────────────────────
15:32:45  GET /api/users          200  45ms  ✓ Clean
15:32:44  POST /api/orders        201  123ms ✓ Clean
15:32:43  GET /api/products       200  67ms  ✓ Clean
15:32:42  POST /api/login         200  234ms ⚠️  Suspicious IP
15:32:41  GET /api/users?id=1'    403  2ms   ❌ SQL Injection Blocked
```

#### 3. Security Events
```
Last 24 Hours:
─────────────────────────────────────────────────
✓ 45,000 Clean requests
⚠️  234 Suspicious requests (flagged)
❌ 12 Blocked attacks
  • 8 SQL injection attempts
  • 3 XSS attempts
  • 1 DDoS pattern detected
```

#### 4. Top Endpoints
```
Endpoint                Requests    Avg Response
────────────────────────────────────────────────
GET /api/users          12,345      45ms
POST /api/orders        8,234       156ms
GET /api/products       6,789       67ms
POST /api/login         3,456       234ms
```

#### 5. Geographic Distribution
```
Country         Requests    % Total
─────────────────────────────────────
Egypt           25,000      55%
Saudi Arabia    10,000      22%
UAE             7,000       15%
Kuwait          2,000       4%
Other           1,234       3%
```

---

## 🔐 PHASE 5: CONFIGURATION & MANAGEMENT

### Managing Applications

Customer can configure via dashboard:

#### 1. Rate Limits (Per Application)
```
Rate Limits for: Acme API Server
────────────────────────────────────
Per Minute:  [1000] requests
Per Hour:    [10000] requests  
Per Day:     [100000] requests

[Save Changes]
```

#### 2. IP Blocking/Allowing
```
IP Access Control
────────────────────────────────────
Blocked IPs:
  • 192.168.1.100 (Suspicious activity)
  • 10.0.0.50 (DDoS source)
  [+ Add IP]

Allowed IPs (whitelist):
  • 203.0.113.0/24 (Office network)
  [+ Add IP Range]

[Save Changes]
```

#### 3. Geographic Blocking
```
Geographic Access Control
────────────────────────────────────
Block Countries:
  ☐ All countries except selected
  ☑ Specific countries:
    ☑ Russia
    ☑ China
    ☑ North Korea
  
Allow Countries:
  ☑ Egypt
  ☑ Saudi Arabia
  ☑ UAE
  ☑ All Middle East

[Save Changes]
```

#### 4. Custom Rules
```
Security Rules
────────────────────────────────────
Rule 1: Block requests with SQL keywords
  Pattern: (?i)(SELECT|INSERT|UPDATE|DELETE|DROP)
  Action: Block
  Status: ✓ Active

Rule 2: Require authentication header
  Header: Authorization
  Required: Yes
  Action: Block if missing
  Status: ✓ Active

[+ Add New Rule]
```

---

## 📈 PHASE 6: MONITORING & ALERTS

### Real-Time Monitoring

Customer receives alerts via:
- 📧 Email
- 💬 Slack
- 📱 SMS (Enterprise only)
- 🔔 Dashboard notifications

**Alert Examples**:

#### Alert 1: Quota Warning
```
⚠️  SENTRIX Alert: Quota Warning

Your application "Acme API Server" has used 80% 
of monthly quota.

Current Usage: 800,000 / 1,000,000 requests
Remaining: 200,000 requests (20%)
Days Left: 15 days

Action Required:
• Upgrade plan to avoid service interruption
• Or optimize request volume

[Upgrade Plan] [View Usage]
```

#### Alert 2: Security Threat
```
🚨 SENTRIX Alert: Security Threat Detected

Multiple SQL injection attempts detected:
• Time: 2025-11-01 15:30:00
• Source IP: 192.168.1.100
• Endpoint: /api/users
• Status: Blocked automatically

12 attempts blocked in last 5 minutes.
IP has been auto-blocked for 24 hours.

[View Details] [Manage IP Blocks]
```

#### Alert 3: Performance Issue
```
⚠️  SENTRIX Alert: Performance Degradation

Your backend response time has increased:
• Endpoint: POST /api/orders
• Avg Response: 2.3s (normally 156ms)
• Since: 15:00
• Affected Requests: 234

This may indicate:
• Database issue
• High load on backend
• Network problem

[View Performance Dashboard] [Check Backend Status]
```

---

## 🔄 PHASE 7: ONGOING MANAGEMENT

### Weekly Tasks (5 minutes)

1. **Review Dashboard**
   - Check quota usage
   - Review security events
   - Monitor performance

2. **Adjust Settings** (if needed)
   - Update rate limits
   - Manage IP blocks
   - Review custom rules

3. **Check Reports**
   - Weekly security summary email
   - Usage trends
   - Cost optimization tips

---

### Monthly Tasks (10 minutes)

1. **Review Subscription**
   - Check if quota is sufficient
   - Consider upgrade/downgrade
   - Review costs vs. value

2. **Security Audit**
   - Review blocked attacks
   - Update security rules
   - Check compliance reports

3. **Optimize Performance**
   - Review slow endpoints
   - Adjust cache settings
   - Configure CDN (if needed)

---

## 💳 PHASE 8: BILLING & PAYMENT

### Trial Period (14 days)

**During Trial**:
```
Status: Trial Active
Days Remaining: 12 days
Full Access: ✓ All features enabled
Payment: Not required yet

[Add Payment Method]
```

### Adding Payment Method

Customer goes to: `Dashboard → Billing`

```
Billing Information
────────────────────────────────────
Plan: Startup ($149/mo)
Billing Cycle: ○ Monthly  ● Annual ($1,490/yr - Save $298!)

Payment Method:
  ○ Credit Card
  ○ PayPal
  ○ Bank Transfer (Enterprise only)

Card Information:
  Card Number: [____-____-____-____]
  Expiry: [MM/YY]  CVV: [___]
  Name: [John Doe]

[Save & Start Subscription]
```

### After Trial Ends

**If Payment Added**:
- Automatically converts to paid subscription
- No service interruption
- Invoice sent via email

**If No Payment**:
- Downgrade to Free plan automatically
- Email reminder 3 days before
- Limited to 10K requests/month

---

## 📊 PHASE 9: SCALING UP

### When Customer Needs More

#### Scenario 1: Approaching Quota Limit

**Dashboard Shows**:
```
⚠️  Warning: 90% Quota Used

Current Plan: Startup (1M requests/mo)
Used: 900,000 requests
Remaining: 100,000 (10%)
Days Left: 5 days

Recommended: Upgrade to Business Plan
  • 10M requests/month (10x more)
  • $399/month
  • Upgrade now with prorated billing

[Upgrade Now] [View Plans]
```

Customer clicks "Upgrade Now":
1. Selects new plan (Business)
2. Confirms upgrade
3. Pays prorated difference
4. Quota increases immediately

---

#### Scenario 2: Adding More Applications

Customer wants to protect additional services:

**Dashboard → Applications → Add New**:
```
Add New Application
────────────────────────────────────
Environment: [Production ▼]

Application Name: [Acme Mobile API]
Base URL: [https://mobile.acmeapp.com]
Target URL: [https://api-mobile.acmeapp.com]

Framework: [Node.js ▼]
Language: [JavaScript ▼]

Quota Allocation:
  From: Production environment (5M remaining)
  Allocate: [500000] requests/month

[Create Application]
```

Result:
- New API key generated: `sentrix_live_Xyz789Uvw456...`
- Quota allocated from environment pool
- Ready to integrate in minutes

---

#### Scenario 3: Adding New Environment

Customer wants staging environment:

**Dashboard → Environments → Add New**:
```
Add New Environment
────────────────────────────────────
Name: [Staging]
Type: [Staging ▼]
Description: [Pre-production testing]

Quota Allocation:
  From: Organization pool (8M remaining)
  Allocate: [2000000] requests/month

[Create Environment]
```

Then add applications under that environment.

---

## 🎯 COMPLETE CUSTOMER WORKFLOW DIAGRAM

```
                    SENTRIX CUSTOMER JOURNEY
                    ========================

1. SIGNUP (2 min)
   └─> Create account → Choose plan → Setup apps → Get API keys

2. INTEGRATION (10 min)
   └─> Update code → Add API key → Change endpoint → Deploy

3. TESTING (5 min)
   └─> Test API key → Make requests → Verify security

4. GO LIVE ✓
   └─> Switch traffic → Monitor dashboard

5. DAILY USAGE (ongoing)
   ├─> Automatic Protection (0 effort)
   ├─> Monitor Dashboard (5 min/day)
   ├─> Review Alerts (as needed)
   └─> Adjust Settings (as needed)

6. MONTHLY BILLING (automatic)
   └─> Auto-charge card → Invoice sent → Service continues

7. SCALING (as needed)
   └─> Upgrade plan OR Add apps OR Add environments

                    ✓ PROTECTED!
```

---

## ✅ BENEFITS FOR CUSTOMER

### Before SENTRIX:
- ❌ Vulnerable to attacks
- ❌ No visibility into threats
- ❌ Manual security monitoring
- ❌ No rate limiting
- ❌ Risk of DDoS
- ❌ No behavioral analysis

### After SENTRIX:
- ✅ **Automatic Protection**: Real-time threat blocking
- ✅ **Complete Visibility**: Dashboard shows everything
- ✅ **AI-Powered**: Behavioral analysis detects anomalies
- ✅ **Rate Limiting**: Prevents abuse automatically
- ✅ **DDoS Protection**: Automatic detection and mitigation
- ✅ **Compliance**: Audit logs for regulations
- ✅ **Peace of Mind**: 24/7 automated security

---

## 💡 CUSTOMER SUCCESS METRICS

After 30 days with SENTRIX, typical customer sees:

```
Security Improvements:
─────────────────────────────────────
  ✓ 99.9% uptime maintained
  ✓ 1,234 attacks blocked automatically
  ✓ 0 successful breaches
  ✓ 45ms average overhead (minimal impact)

Cost Savings:
─────────────────────────────────────
  ✓ $0 cost from DDoS attacks
  ✓ $0 data breach costs
  ✓ 20 hours/month saved on manual monitoring
  ✓ ROI: 10x (vs. building in-house)

Performance:
─────────────────────────────────────
  ✓ <10ms added latency
  ✓ 99.99% request success rate
  ✓ Geographic routing (faster responses)
  ✓ Built-in caching (optional)
```

---

## 🎉 SUMMARY

### Customer's Experience with SENTRIX:

1. **Sign Up**: 2 minutes
2. **Setup**: 5 minutes  
3. **Integration**: 10 minutes
4. **Testing**: 5 minutes
5. **Total Time**: **~30 minutes to full protection**

### Ongoing Effort:
- **Daily**: 0 minutes (automatic)
- **Weekly**: 5 minutes (dashboard review)
- **Monthly**: 10 minutes (reports & optimization)

### Value Delivered:
- ✅ Enterprise-grade security
- ✅ Real-time threat protection
- ✅ AI-powered behavioral analysis
- ✅ Complete visibility
- ✅ Compliance support
- ✅ 24/7 automated protection

**Total Cost**: $149-1,499/month  
**vs. Building In-House**: $50,000+ upfront + $10,000+/month

**ROI**: 10-50x 🚀

---

*Last Updated: November 2025*  
*For support: support@sentrix.io*  
*Documentation: https://docs.sentrix.io*

