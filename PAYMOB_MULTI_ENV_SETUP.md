# Paymob Billing: Multi-Environment Setup (SENTRIX Side)

## Overview
Customer: Paymob Solutions
Application: Billing Portal
Environments: Staging + Production (separate domains)
Mode: DNS (Zero-Deployment)

---

## ✅ SENTRIX Configuration (Your Side)

### Environment 1: Staging

```bash
# 1. Create Organization & Staging App
POST /api/onboarding/quick_start/
Authorization: Token paymob_auth_token
{
  "organization_name": "Paymob Solutions",
  "plan_type": "business",
  "environments": [{
    "name": "Staging",
    "environment_type": "staging",
    "allocated_quota": 1000000,  # 1M requests/month for staging
    "applications": [{
      "name": "Billing Portal - Staging",
      "base_url": "https://stg-bills.paymobsolutions.com",
      "target_url": "http://10.0.1.50:8000",  # Paymob's staging origin
      "rate_limit_per_minute": 500,
      "rate_limit_per_hour": 10000
    }]
  }]
}
```

**Response:**
```json
{
  "organization": {
    "id": "org-paymob-123",
    "name": "Paymob Solutions"
  },
  "applications": [{
    "id": "app-staging-456",
    "name": "Billing Portal - Staging",
    "api_key": "sentrix_live_staging_xyz"  // ⚠️ Generated but NOT needed for DNS mode
  }]
}
```

```bash
# 2. Start DNS Onboarding for Staging
POST /api/applications/onboarding-wizard/start/
Authorization: Token paymob_auth_token
{
  "domain": "stg-bills.paymobsolutions.com",
  "origin_url": "http://10.0.1.50:8000",
  "application_name": "Billing Portal - Staging"
}
```

**Response (DNS records for Paymob):**
```json
{
  "application_id": "app-staging-456",
  "domain": "stg-bills.paymobsolutions.com",
  "edge_hostname": "c-staging-456.edge.sentrix-co.com",
  
  "dns_records": {
    "verification": {
      "type": "TXT",
      "name": "_sentrix-verify.stg-bills.paymobsolutions.com",
      "value": "sentrix-verify=staging-abc123def456",
      "ttl": 300
    },
    "routing": {
      "type": "CNAME",
      "name": "stg-bills.paymobsolutions.com",
      "value": "c-staging-456.edge.sentrix-co.com",
      "ttl": 300
    }
  },
  
  "instructions_for_customer": [
    "Add these DNS records to paymobsolutions.com DNS provider",
    "Wait 2-5 minutes for auto-verification",
    "No code changes needed in your application",
    "Your staging environment will be automatically protected"
  ]
}
```

---

### Environment 2: Production

```bash
# 1. Create Production App (same organization)
POST /api/onboarding/quick_start/
Authorization: Token paymob_auth_token
{
  "organization_name": "Paymob Solutions",  # Same org
  "plan_type": "enterprise",  # Higher tier for production
  "environments": [{
    "name": "Production",
    "environment_type": "production",
    "allocated_quota": 5000000,  # 5M requests/month for production
    "applications": [{
      "name": "Billing Portal - Production",
      "base_url": "https://bills.paymobsolutions.com",
      "target_url": "http://10.0.2.100:8000",  # Paymob's production origin
      "rate_limit_per_minute": 2000,
      "rate_limit_per_hour": 50000
    }]
  }]
}
```

**Response:**
```json
{
  "organization": {
    "id": "org-paymob-123",  // Same org ID
    "name": "Paymob Solutions"
  },
  "applications": [{
    "id": "app-production-789",
    "name": "Billing Portal - Production",
    "api_key": "sentrix_live_production_abc"  // ⚠️ Generated but NOT needed for DNS mode
  }]
}
```

```bash
# 2. Start DNS Onboarding for Production
POST /api/applications/onboarding-wizard/start/
Authorization: Token paymob_auth_token
{
  "domain": "bills.paymobsolutions.com",
  "origin_url": "http://10.0.2.100:8000",
  "application_name": "Billing Portal - Production"
}
```

**Response (DNS records for Paymob):**
```json
{
  "application_id": "app-production-789",
  "domain": "bills.paymobsolutions.com",
  "edge_hostname": "c-production-789.edge.sentrix-co.com",
  
  "dns_records": {
    "verification": {
      "type": "TXT",
      "name": "_sentrix-verify.bills.paymobsolutions.com",
      "value": "sentrix-verify=production-xyz789def",
      "ttl": 300
    },
    "routing": {
      "type": "CNAME",
      "name": "bills.paymobsolutions.com",
      "value": "c-production-789.edge.sentrix-co.com",
      "ttl": 300
    }
  },
  
  "instructions_for_customer": [
    "Add these DNS records to paymobsolutions.com DNS provider",
    "Test staging first to validate the setup",
    "Schedule production DNS update during low-traffic window",
    "Monitor SENTRIX dashboard for verification status"
  ]
}
```

---

## 📧 Send to Customer (Paymob)

### Email Template:

```
Subject: SENTRIX DNS Records for Billing Portal Protection

Hi Paymob Team,

Your billing application is ready to be protected with SENTRIX. 
Please add the following DNS records to your DNS provider.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STAGING ENVIRONMENT: stg-bills.paymobsolutions.com

DNS Records to Add:
1. TXT Record (for verification):
   Name:  _sentrix-verify.stg-bills.paymobsolutions.com
   Value: sentrix-verify=staging-abc123def456
   TTL:   300

2. CNAME Record (to route traffic):
   Name:  stg-bills.paymobsolutions.com
   Value: c-staging-456.edge.sentrix-co.com
   TTL:   300

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PRODUCTION ENVIRONMENT: bills.paymobsolutions.com

DNS Records to Add:
1. TXT Record (for verification):
   Name:  _sentrix-verify.bills.paymobsolutions.com
   Value: sentrix-verify=production-xyz789def
   TTL:   300

2. CNAME Record (to route traffic):
   Name:  bills.paymobsolutions.com
   Value: c-production-789.edge.sentrix-co.com
   TTL:   300

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPORTANT NOTES:

✅ NO CODE CHANGES NEEDED
   - Your application code remains unchanged
   - No redeployment required
   - No configuration file updates
   - No restart needed

✅ ZERO DOWNTIME
   - DNS update happens gradually
   - Your application keeps running
   - Rollback is instant if needed

✅ AUTOMATIC VERIFICATION
   - We check DNS records every 5 minutes
   - You'll receive email when verified
   - Protection activates automatically

🔄 RECOMMENDED ROLLOUT:
   1. Add STAGING DNS first
   2. Wait for verification (2-5 min)
   3. Test staging thoroughly
   4. Add PRODUCTION DNS
   5. Monitor production traffic

📊 MONITORING:
   Dashboard: https://dashboard.sentrix-co.com
   Username: your-paymob-email
   
   Real-time view of:
   - Protected requests
   - Blocked attacks
   - Performance metrics

🆘 ROLLBACK (if needed):
   Simply remove the CNAME record to revert back.
   Takes effect in 5 minutes (TTL).

Questions? Reply to this email or call us at: +20 xxx xxx xxxx

Best regards,
SENTRIX Team
```

---

## 🔍 Monitoring (SENTRIX Dashboard)

### What You'll See:

```
Organization: Paymob Solutions
├── Staging Environment
│   └── Billing Portal - Staging
│       ├── Domain: stg-bills.paymobsolutions.com
│       ├── Status: ✅ Verified
│       ├── Traffic Mode: DNS
│       ├── Requests: 45,231 today
│       ├── Blocked: 127 attacks
│       └── Latency: ~28ms
│
└── Production Environment
    └── Billing Portal - Production
        ├── Domain: bills.paymobsolutions.com
        ├── Status: ✅ Verified
        ├── Traffic Mode: DNS
        ├── Requests: 2,145,678 today
        ├── Blocked: 3,421 attacks
        └── Latency: ~26ms
```

---

## ⚙️ SENTRIX Edge Configuration

### Edge Routing Logic:

```python
# edge/main.py

async def proxy_request(request: Request):
    """
    Route request based on Host header (DNS mode)
    NO API KEY NEEDED!
    """
    
    # Get the Host header
    host = request.headers.get("Host")  # e.g., "stg-bills.paymobsolutions.com"
    
    # Resolve application by domain
    if host == "stg-bills.paymobsolutions.com":
        app_config = {
            "id": "app-staging-456",
            "target_url": "http://10.0.1.50:8000",
            "rate_limit_per_minute": 500,
            "origin_signature_key": "staging-sig-key-abc"
        }
    
    elif host == "bills.paymobsolutions.com":
        app_config = {
            "id": "app-production-789",
            "target_url": "http://10.0.2.100:8000",
            "rate_limit_per_minute": 2000,
            "origin_signature_key": "production-sig-key-xyz"
        }
    
    else:
        # Domain not registered
        return JSONResponse(
            {"error": "unauthorized", "message": "Domain not recognized"},
            status_code=401
        )
    
    # Apply security checks
    await check_sql_injection(request)
    await check_xss(request)
    await check_rate_limit(app_config["id"], client_ip)
    
    # Proxy to origin with signature
    proxied_request = add_sentrix_signature(request, app_config["origin_signature_key"])
    response = await proxy_to_origin(app_config["target_url"], proxied_request)
    
    return response
```

**Key Point:** Edge identifies application by **Host header**, not API key!

---

## 🎯 Summary of Changes

### SENTRIX Side (Your Work):

```
✅ Register 2 applications:
   1. Staging: stg-bills.paymobsolutions.com
   2. Production: bills.paymobsolutions.com

✅ Generate DNS records for each

✅ Send DNS records to Paymob

✅ Monitor auto-verification (Celery Beat)

✅ Notify Paymob when verified

NO CODE CHANGES ON YOUR END ✅
```

### Paymob Side (Customer Work):

```
✅ Add DNS records (TXT + CNAME) for staging

✅ Add DNS records (TXT + CNAME) for production

❌ NO code changes in ~/Desktop/bills_revamp_updated_repo/bills_portal
❌ NO redeployment
❌ NO configuration changes
❌ NO API keys in code
```

### What Gets Protected:

```
Staging:
  ✅ https://stg-bills.paymobsolutions.com/*
  ✅ All endpoints automatically
  ✅ SQL injection blocked
  ✅ XSS blocked
  ✅ Rate limited: 500 req/min

Production:
  ✅ https://bills.paymobsolutions.com/*
  ✅ All endpoints automatically
  ✅ SQL injection blocked
  ✅ XSS blocked
  ✅ Rate limited: 2000 req/min
```

---

## 💰 Pricing Structure

### Option 1: Separate Plans

```
Staging:  Business Plan ($299/month)
          - 1M requests/month
          - 500 requests/minute

Production: Enterprise Plan ($999/month)
            - 5M requests/month
            - 2000 requests/minute

Total: $1,298/month
```

### Option 2: Combined (Recommended)

```
Single Enterprise Plan ($999/month)
  - 5M requests/month (shared across both)
  - Staging: 500 requests/minute
  - Production: 2000 requests/minute
  - Both environments under one organization
  - Single dashboard view

Total: $999/month
```

**Recommendation:** Option 2 (single enterprise plan, multiple applications)

---

## 🔄 Deployment Timeline

### Week 1: Staging
- Day 1: Register staging in SENTRIX
- Day 1: Send DNS records to Paymob
- Day 2: Paymob adds DNS records
- Day 2: Auto-verification completes
- Day 2-7: Monitor staging, validate protection

### Week 2: Production
- Day 8: Register production in SENTRIX
- Day 8: Send DNS records to Paymob
- Day 9: Paymob schedules DNS update (low-traffic window)
- Day 9: Add production DNS records
- Day 9: Auto-verification completes
- Day 10-14: Monitor production metrics

### Week 3: Optimization
- Review attack patterns
- Tune rate limits if needed
- Configure custom rules (if any)
- Training session for Paymob team

---

## ✅ Success Criteria

### Staging:
- [ ] DNS records added
- [ ] Domain verified (dns_status = 'verified')
- [ ] All staging endpoints accessible
- [ ] No performance degradation
- [ ] Attacks being blocked (visible in dashboard)

### Production:
- [ ] DNS records added
- [ ] Domain verified
- [ ] All production endpoints accessible
- [ ] Latency < 50ms overhead
- [ ] Zero downtime during cutover
- [ ] Paymob team trained on dashboard

---

## 🆘 Support Plan

### For Paymob:
- Email: support@sentrix-co.com
- Phone: +20 xxx xxx xxxx (24/7 for production)
- Dashboard: https://dashboard.sentrix-co.com
- Documentation: https://docs.sentrix-co.com

### Escalation:
- P1 (Production down): Immediate response
- P2 (Performance issue): < 30 min response
- P3 (General questions): < 2 hours response

---

## 🎉 Final Notes

**This is the PERFECT use case for DNS mode!**

✅ Staging and Production as separate domains
✅ Zero code changes needed
✅ Zero downtime migration
✅ Independent protection per environment
✅ NO API KEYS in code
✅ Transparent to developers
✅ Easy rollback if needed

**Paymob just adds DNS records and they're protected!** 🎉

