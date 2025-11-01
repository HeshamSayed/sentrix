# SENTRIX Integration Modes Guide

## Choose Your Integration Mode

SENTRIX supports **two integration modes**. Customers choose ONE based on their needs:

---

## 🌟 Mode 1: DNS Mode (Zero-Deployment) - RECOMMENDED

### Perfect For:
- Existing production applications
- Teams who want zero code changes
- Protecting entire domains/subdomains
- Fastest time-to-protection (minutes)

### Customer Journey:
1. **Sign up** to SENTRIX
2. **Add DNS records** (we provide exact records)
3. **Wait 2-5 minutes** for auto-verification
4. **Done!** All traffic automatically protected

### Example:
```bash
# Customer owns: api.todo.com (running on their server at todo.com:8000)

# Step 1: Add DNS records
CNAME api.todo.com → c-abc123.edge.sentrix-co.com
TXT _sentrix-verify.api.todo.com → verification-token-xyz

# Step 2: Wait for auto-verification (Celery Beat checks every 5 min)
# Step 3: PROTECTED! No code changes needed.
```

### How It Works:
```
┌─────────┐       DNS        ┌──────────────┐      Proxy       ┌────────────┐
│  User   │ ─────────────> │ SENTRIX Edge │ ──────────────> │   Origin   │
└─────────┘                 └──────────────┘                 └────────────┘
            api.todo.com      Host: api.todo.com              todo.com:8000
            (via DNS)         → Lookup app config              + Signature
                             → Security checks
                             → Rate limiting
                             → Behavioral analysis
```

### Security:
- **Traffic Identification**: Host header
- **Origin Protection**: X-SENTRIX-Signature header (optional but recommended)
- **Failover**: Automatic with bypass token

### Pricing Impact:
- Charged per domain
- All endpoints under domain protected
- Unlimited requests (within subscription plan)

---

## 🔑 Mode 2: API Key Mode (Code Integration)

### Perfect For:
- Multiple environments on same domain (dev/staging/prod)
- Selective endpoint protection
- Development and testing phase
- Teams who prefer explicit integration
- Per-key rate limiting

### Customer Journey:
1. **Sign up** to SENTRIX
2. **Get API key** from dashboard
3. **Update application code** to add header
4. **Deploy** updated code
5. **Done!** Protected endpoints use SENTRIX

### Example:
```javascript
// Customer's application code

// BEFORE (unprotected):
const response = await fetch('https://api.todo.com/todos');

// AFTER (protected via SENTRIX):
const response = await fetch('https://edge.sentrix-co.com/api/todos', {
  headers: {
    'X-SENTRIX-Key': 'sentrix_live_abc123xyz...'
  }
});
```

### How It Works:
```
┌─────────┐    + API Key     ┌──────────────┐      Proxy       ┌────────────┐
│   App   │ ─────────────> │ SENTRIX Edge │ ──────────────> │   Origin   │
└─────────┘                 └──────────────┘                 └────────────┘
            X-SENTRIX-Key     → Validate key                  target_url
            edge.sentrix.com  → Get app config                + Signature
                             → Security checks
```

### Security:
- **Traffic Identification**: X-SENTRIX-Key header
- **Origin Protection**: X-SENTRIX-Signature header (optional)
- **Granular Control**: Per-endpoint protection

### Pricing Impact:
- Charged per API key
- Only protected endpoints count towards quota
- Rate limiting per key

---

## 🔄 Hybrid Mode (Advanced)

### Use Both Together:
```
Primary: DNS Mode (all traffic)
  ↓
Secondary: API Key (for admin endpoints requiring extra validation)
```

### Example:
```javascript
// Public API (DNS mode only):
GET https://api.todo.com/todos
// → Protected via DNS, no API key needed in code

// Admin API (DNS + API key):
POST https://api.todo.com/admin/users
Headers: { 'X-SENTRIX-Key': 'sentrix_live_admin_key' }
// → Double protection: DNS + API key validation
```

---

## 🎯 **Quick Decision Matrix**

| Requirement | DNS Mode | API Key Mode |
|-------------|----------|--------------|
| Zero code changes | ✅ Yes | ❌ No (code update needed) |
| Fastest setup | ✅ < 5 min | ⏱️ Requires deployment |
| Protect entire domain | ✅ Yes | ⚠️ Only specific endpoints |
| Multiple envs same domain | ❌ No | ✅ Yes (different keys) |
| Transparent to app | ✅ Yes | ❌ No (explicit header) |
| Origin protection | ✅ Signature | ✅ Signature |
| Failover support | ✅ Automatic | ⚠️ Manual |
| Per-endpoint control | ⚠️ Via rules | ✅ Native |
| Setup complexity | ⭐ Easy | ⭐⭐ Medium |

---

## 📊 **Recommended Setup by Use Case**

### **SaaS Application (api.saas.com)**
→ **DNS Mode** ✨
- Zero downtime migration
- No code changes
- Automatic failover
- Wildcard protection

### **Microservices (Multiple APIs)**
→ **API Key Mode per Service**
- service-a: Key A (rate limit: 1000/min)
- service-b: Key B (rate limit: 5000/min)
- service-c: Key C (rate limit: 100/min)

### **Mobile App Backend**
→ **API Key Mode**
- Embed key in app
- Rotate keys per app version
- Track usage per version

### **E-commerce Site (shop.example.com)**
→ **DNS Mode** ✨
- Protect all pages
- No JavaScript changes
- SEO-friendly (same domain)

---

## 🛠️ **Implementation Notes**

### For DNS Mode:
```python
# backend/applications/views.py - resolve_host endpoint
# Called by Edge when request has no API key but has Host header

def resolve_host(request):
    host = request.query_params.get('host')
    application = Application.objects.get(
        protected_domain=host,
        traffic_mode='dns',
        dns_status='verified'
    )
    return application_config
```

### For API Key Mode:
```python
# backend/applications/views.py - validate_key endpoint
# Called by Edge when request has X-SENTRIX-Key header

def validate_key(request):
    api_key = request.headers.get('X-SENTRIX-Key')
    application = Application.objects.get(api_key=api_key)
    return application_config
```

### Edge Service Logic:
```python
# edge/main.py - proxy_request function

async def proxy_request(request):
    # Try API key first
    if api_key := request.headers.get('X-SENTRIX-Key'):
        app_config = await check_api_key(api_key)
    
    # Fallback to DNS mode
    elif host := request.headers.get('Host'):
        app_config = await resolve_by_host(host)
    
    # No valid authentication
    else:
        return 401 Unauthorized
    
    # Proxy to origin with signature
    return await proxy_to_origin(app_config, request)
```

---

## 💰 **Pricing Considerations**

### DNS Mode:
- **Billed by domain**: `api.todo.com` = 1 protected domain
- **All endpoints included**: `/users`, `/todos`, `/admin/*` all protected
- **Wildcard support**: `*.api.todo.com` = unlimited subdomains

### API Key Mode:
- **Billed by requests**: Only requests with API key count
- **Granular tracking**: Per-endpoint analytics
- **Multiple keys**: Different limits per key

### Recommendation:
- **Small teams**: DNS Mode (simpler, predictable pricing)
- **Enterprise**: Hybrid (DNS for public API + Keys for internal services)

---

## 🚀 **Migration Path**

### Phase 1: Development (API Key Mode)
```javascript
// Test SENTRIX integration in dev
fetch('https://edge.sentrix-co.com/api/test', {
  headers: { 'X-SENTRIX-Key': 'sentrix_test_key' }
})
```

### Phase 2: Staging (DNS Mode)
```bash
# Switch staging environment to DNS
CNAME staging-api.todo.com → c-staging.edge.sentrix-co.com
```

### Phase 3: Production (DNS Mode)
```bash
# Zero-downtime production cutover
CNAME api.todo.com → c-prod.edge.sentrix-co.com
```

### Phase 4: Cleanup
```javascript
// Remove API key from code (now using DNS mode)
// Old: fetch('https://edge.sentrix-co.com/...')
// New: fetch('https://api.todo.com/...') // DNS routes to SENTRIX
```

---

## 📝 **Summary**

**Choose DNS Mode if:**
- ✅ You want zero code changes
- ✅ You need fast deployment
- ✅ You're protecting production apps
- ✅ You want automatic failover

**Choose API Key Mode if:**
- ✅ You need granular control
- ✅ You have multiple environments
- ✅ You're in development phase
- ✅ You want per-key analytics

**Most customers should start with DNS Mode** - it's the easiest, fastest, and most transparent way to protect your applications.

---

## 🔗 **Related Documentation**

- `DNS_ZERO_DEPLOY_DEMO.md` - Step-by-step DNS setup
- `ZERO_DOWNTIME_FAILOVER.md` - Failover configuration
- `AUTOMATED_SELF_SERVICE_ONBOARDING.md` - Complete onboarding guide
- `E2E_TEST_STATUS.md` - Testing both modes

