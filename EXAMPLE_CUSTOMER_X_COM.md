# 🛡️ How to Protect x.com with SENTRIX - Complete Journey

## Your Scenario

**Your Website**: `x.com`  
**Your API**: `api.x.com`  
**Goal**: Protect your API from attacks  
**Question**: Do I need to deploy anything on my side?  
**Answer**: **YES, but it's SUPER SIMPLE** (only 2 changes!)

---

## 📋 STEP-BY-STEP JOURNEY

### STEP 1: Sign Up to SENTRIX (2 minutes)

#### 1.1 Go to SENTRIX Website
Visit: `https://sentrix.io/signup`

#### 1.2 Fill Registration Form
```
Email: you@x.com
Password: YourSecurePassword123!
First Name: Your Name
Last Name: Your Last Name
Company: x.com Inc
```

**Click**: "Create Account"

#### 1.3 You Get
✅ Account created  
✅ Authentication token  
✅ Access to dashboard

---

### STEP 2: Choose Your Plan (1 minute)

You see 4 plans:

```
┌─────────────────────────────────────────────────────┐
│ 💎 Free - $0/month                                  │
│    • 10,000 requests/month                          │
│    • Good for testing only                          │
├─────────────────────────────────────────────────────┤
│ 🚀 Startup - $149/month ⭐ RECOMMENDED              │
│    • 1,000,000 requests/month                       │
│    • Perfect for growing websites                   │
│    • 14-day FREE trial                              │
├─────────────────────────────────────────────────────┤
│ 💼 Business - $399/month                            │
│    • 10,000,000 requests/month                      │
│    • For high-traffic websites                      │
├─────────────────────────────────────────────────────┤
│ 🏢 Enterprise - $1,499/month                        │
│    • 100,000,000 requests/month                     │
│    • For massive scale                              │
└─────────────────────────────────────────────────────┘
```

**You Choose**: "Startup" (14-day free trial!)

---

### STEP 3: Setup Your Application (2 minutes)

#### 3.1 Fill in Your Details

```
Organization Name: x.com Inc
Plan: Startup ($149/mo with 14-day trial)

Environment Setup:
┌─────────────────────────────────────────────┐
│ Environment 1: Production                   │
│ ├─ Application: x.com API                   │
│ ├─ Your API URL: https://api.x.com          │
│ └─ Base URL: https://x.com                  │
└─────────────────────────────────────────────┘

[Optional] Add more environments?
□ Staging
□ Development

[Continue]
```

**Click**: "Continue"

---

#### 3.2 You Receive Your API Key 🔑

```
╔════════════════════════════════════════════════╗
║  ✅ Setup Complete!                           ║
╚════════════════════════════════════════════════╝

Your SENTRIX API Key:
─────────────────────────────────────────────────
sentrix_live_Abc123Def456Ghi789Jkl012Mno345Pqr
─────────────────────────────────────────────────

⚠️  IMPORTANT: Save this key securely!
   You'll need it for integration.

SENTRIX Edge Endpoint:
─────────────────────────────────────────────────
https://edge.sentrix.io
─────────────────────────────────────────────────

Trial Period: 14 days (No credit card required!)
```

**Copy and save** your API key!

---

## 🔧 STEP 4: INTEGRATION (The Part You Deploy)

### Current Setup (BEFORE SENTRIX):

```
Your Frontend/Mobile App
         ↓
   https://api.x.com/endpoint
         ↓
   Your Backend Server
```

**Problem**: Direct exposure to attacks! ❌

---

### New Setup (AFTER SENTRIX):

```
Your Frontend/Mobile App
         ↓
   https://edge.sentrix.io/endpoint
   (with X-SENTRIX-Key header)
         ↓
   SENTRIX Edge (Security Layer) 🛡️
         ↓
   https://api.x.com/endpoint
         ↓
   Your Backend Server
```

**Solution**: SENTRIX protects you! ✅

---

## 💻 WHAT YOU NEED TO CHANGE

### Option A: Frontend/Mobile App Changes (Recommended for You)

#### If You Have a React/Next.js Frontend:

**BEFORE SENTRIX** (`src/api/client.js`):
```javascript
// Old code - Direct call to your API
const API_BASE_URL = 'https://api.x.com';

export async function getUsers() {
  const response = await fetch(`${API_BASE_URL}/api/users`, {
    headers: {
      'Authorization': `Bearer ${userToken}`,
      'Content-Type': 'application/json'
    }
  });
  return response.json();
}
```

---

**AFTER SENTRIX** (`src/api/client.js`) - **ONLY 2 CHANGES**:
```javascript
// New code - Protected by SENTRIX
const API_BASE_URL = 'https://edge.sentrix.io';  // ← CHANGE 1: New endpoint
const SENTRIX_API_KEY = 'sentrix_live_Abc123Def456Ghi789Jkl012Mno345Pqr';  // ← Your key

export async function getUsers() {
  const response = await fetch(`${API_BASE_URL}/api/users`, {
    headers: {
      'X-SENTRIX-Key': SENTRIX_API_KEY,  // ← CHANGE 2: Add this header
      'Authorization': `Bearer ${userToken}`,  // Keep your existing headers
      'Content-Type': 'application/json'
    }
  });
  return response.json();
}
```

**That's it!** Just 2 changes:
1. Change endpoint to `edge.sentrix.io`
2. Add `X-SENTRIX-Key` header

---

#### Better Way - Using Environment Variables:

**Step 1**: Add to your `.env` file:
```bash
# .env.local (for Next.js) or .env (for React)
NEXT_PUBLIC_SENTRIX_ENABLED=true
NEXT_PUBLIC_SENTRIX_API_KEY=sentrix_live_Abc123Def456Ghi789Jkl012Mno345Pqr
NEXT_PUBLIC_SENTRIX_EDGE_URL=https://edge.sentrix.io
NEXT_PUBLIC_API_BASE_URL=https://api.x.com
```

**Step 2**: Update your API client:
```javascript
// src/api/client.js
const SENTRIX_ENABLED = process.env.NEXT_PUBLIC_SENTRIX_ENABLED === 'true';
const API_BASE_URL = SENTRIX_ENABLED 
  ? process.env.NEXT_PUBLIC_SENTRIX_EDGE_URL
  : process.env.NEXT_PUBLIC_API_BASE_URL;

export async function getUsers() {
  const headers = {
    'Authorization': `Bearer ${userToken}`,
    'Content-Type': 'application/json'
  };

  // Add SENTRIX key if enabled
  if (SENTRIX_ENABLED) {
    headers['X-SENTRIX-Key'] = process.env.NEXT_PUBLIC_SENTRIX_API_KEY;
  }

  const response = await fetch(`${API_BASE_URL}/api/users`, { headers });
  return response.json();
}
```

**Benefits**:
- ✅ Easy to turn on/off
- ✅ Secure (key in .env)
- ✅ Works for all your API calls
- ✅ Can test before going live

---

#### If You Have Mobile Apps:

**iOS (Swift)**:
```swift
// Before SENTRIX
let url = URL(string: "https://api.x.com/api/users")!
var request = URLRequest(url: url)
request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

// After SENTRIX - Just 2 changes
let url = URL(string: "https://edge.sentrix.io/api/users")!  // Change 1
var request = URLRequest(url: url)
request.addValue("sentrix_live_Abc123...", forHTTPHeaderField: "X-SENTRIX-Key")  // Change 2
request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
```

**Android (Kotlin)**:
```kotlin
// Before SENTRIX
val request = Request.Builder()
    .url("https://api.x.com/api/users")
    .addHeader("Authorization", "Bearer $token")
    .build()

// After SENTRIX - Just 2 changes
val request = Request.Builder()
    .url("https://edge.sentrix.io/api/users")  // Change 1
    .addHeader("X-SENTRIX-Key", "sentrix_live_Abc123...")  // Change 2
    .addHeader("Authorization", "Bearer $token")
    .build()
```

---

### Option B: Backend Proxy (Zero Client Changes!) 🎯

**If you want ZERO changes to your frontend/mobile apps**, use this option!

#### Using Nginx (Most Common):

**Add this to your nginx config** (`/etc/nginx/sites-available/x.com`):

```nginx
# api.x.com - Proxied through SENTRIX
server {
    listen 443 ssl;
    server_name api.x.com;
    
    ssl_certificate /etc/letsencrypt/live/api.x.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.x.com/privkey.pem;

    location / {
        # Forward ALL requests to SENTRIX Edge
        proxy_pass https://edge.sentrix.io;
        
        # Add your SENTRIX API key
        proxy_set_header X-SENTRIX-Key "sentrix_live_Abc123Def456Ghi789Jkl012Mno345Pqr";
        
        # Forward original headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Your actual backend (not exposed publicly anymore)
server {
    listen 8080;  # Local only
    server_name localhost;
    
    # Your actual backend application
    location / {
        proxy_pass http://localhost:3000;  # Your Node.js/Python/etc app
    }
}
```

**Reload nginx**:
```bash
sudo nginx -t  # Test configuration
sudo systemctl reload nginx  # Apply changes
```

**Done!** ✅ No client-side changes needed!

---

#### Using Cloudflare Workers (Alternative):

```javascript
// Cloudflare Worker for x.com
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  // Get the original URL
  const url = new URL(request.url)
  
  // Change to SENTRIX Edge
  url.hostname = 'edge.sentrix.io'
  
  // Clone request and add SENTRIX key
  const modifiedRequest = new Request(url, {
    method: request.method,
    headers: request.headers,
    body: request.body
  })
  
  // Add SENTRIX API key
  modifiedRequest.headers.set('X-SENTRIX-Key', 'sentrix_live_Abc123Def456Ghi789Jkl012Mno345Pqr')
  
  // Forward to SENTRIX
  return fetch(modifiedRequest)
}
```

---

## 🧪 STEP 5: TESTING (5 minutes)

### Test 1: Verify Your API Key Works

```bash
# Test with curl
curl https://edge.sentrix.io/api/health \
  -H "X-SENTRIX-Key: sentrix_live_Abc123Def456Ghi789Jkl012Mno345Pqr"
```

**Expected Response**:
```json
{
  "status": "ok",
  "protected_by": "SENTRIX",
  "application": "x.com API",
  "organization": "x.com Inc",
  "environment": "Production"
}
```

✅ **Success!** Your API key is valid.

---

### Test 2: Make a Real API Call

```bash
# Test your actual endpoint
curl https://edge.sentrix.io/api/users \
  -H "X-SENTRIX-Key: sentrix_live_Abc123Def456Ghi789Jkl012Mno345Pqr" \
  -H "Authorization: Bearer your-user-token"
```

**What Happens**:
1. SENTRIX receives your request
2. Validates your API key ✓
3. Checks for security threats ✓
4. Proxies to `api.x.com/api/users`
5. Returns response to you
6. Logs everything in dashboard

✅ **Success!** Your requests are now protected.

---

### Test 3: Test Security (Optional)

Try a SQL injection attack:
```bash
curl "https://edge.sentrix.io/api/users?id=1' OR '1'='1" \
  -H "X-SENTRIX-Key: sentrix_live_Abc123Def456Ghi789Jkl012Mno345Pqr"
```

**Expected**: SENTRIX blocks or flags the request!

✅ **Security is working!**

---

## 🚀 STEP 6: GO LIVE

### If Using Option A (Frontend Changes):

**Deployment Steps**:
```bash
# 1. Add SENTRIX key to .env
echo "NEXT_PUBLIC_SENTRIX_API_KEY=sentrix_live_Abc123..." >> .env.production

# 2. Build your app
npm run build

# 3. Deploy to Vercel/Netlify/etc
vercel deploy --prod
# or
npm run deploy
```

✅ **Done!** Your app now uses SENTRIX.

---

### If Using Option B (Nginx Proxy):

**Deployment Steps**:
```bash
# 1. Update nginx config (already done above)

# 2. Test config
sudo nginx -t

# 3. Reload nginx
sudo systemctl reload nginx

# 4. Verify it works
curl https://api.x.com/api/health
```

✅ **Done!** All traffic now goes through SENTRIX (no client changes needed!)

---

## 📊 STEP 7: MONITOR YOUR PROTECTION

### Login to SENTRIX Dashboard

Go to: `https://dashboard.sentrix.io`

**You'll See**:

```
╔════════════════════════════════════════════════════╗
║  x.com Inc - Dashboard                            ║
╠════════════════════════════════════════════════════╣
║                                                    ║
║  📊 Today's Activity                               ║
║  ├─ Requests: 12,345                              ║
║  ├─ Blocked Attacks: 8                            ║
║  ├─ Avg Latency: 8ms                              ║
║  └─ Status: ✅ Healthy                             ║
║                                                    ║
║  🔒 Security Events (Last 24h)                    ║
║  ├─ ✅ Clean: 12,300 requests                      ║
║  ├─ ⚠️  Suspicious: 37 flagged                     ║
║  └─ ❌ Blocked: 8 attacks                          ║
║     • 5 SQL injection attempts                    ║
║     • 2 XSS attempts                              ║
║     • 1 DDoS pattern                              ║
║                                                    ║
║  📈 This Month                                     ║
║  ├─ Requests: 456,789 / 1,000,000 (45%)          ║
║  ├─ Days Left: 18 days                            ║
║  └─ Status: On track ✅                            ║
║                                                    ║
╚════════════════════════════════════════════════════╝

Recent Requests:
────────────────────────────────────────────────────
14:23:45  GET /api/users           200  45ms  ✓
14:23:44  POST /api/posts          201  123ms ✓
14:23:43  GET /api/feed            200  67ms  ✓
14:23:42  GET /api/users?id=1'     403  2ms   ❌ BLOCKED
          ↳ Reason: SQL injection detected
```

---

## ✅ STEP 8: YOU'RE PROTECTED!

### What You Did:
1. ✅ Signed up (2 minutes)
2. ✅ Got API key (instant)
3. ✅ Changed your code (2 changes) or added nginx proxy
4. ✅ Deployed (10 minutes)
5. ✅ Tested (5 minutes)

**Total Time: ~30 minutes** ⏱️

---

### What You Get Now:

#### 🛡️ Security (Automatic):
- ✅ SQL injection protection
- ✅ XSS protection
- ✅ DDoS mitigation
- ✅ Rate limiting
- ✅ IP blocking
- ✅ AI behavioral analysis
- ✅ Real-time threat detection

#### 📊 Visibility:
- ✅ Real-time dashboard
- ✅ Security alerts via email/Slack
- ✅ Request logs
- ✅ Performance metrics
- ✅ Geographic data

#### 💰 Cost:
- ✅ 14-day free trial (no credit card!)
- ✅ $149/month after trial
- ✅ vs. Building it yourself: $50,000+

---

## 🎯 SUMMARY FOR x.com

### Your Journey:
```
Day 1: Sign up → Get API key → Update code → Deploy
       ↓
Day 2-14: FREE TRIAL (test everything)
       ↓
Day 15: Start paying $149/month
       ↓
Ongoing: AUTOMATIC PROTECTION (zero effort!)
```

### What You Deployed:

#### Option A (Frontend):
- Changed API endpoint
- Added API key header
- Total changes: **2 lines of code**

#### Option B (Nginx):
- Updated nginx config
- Added proxy rules
- Total changes: **1 config file**

### Result:
```
Before SENTRIX:
  Your API: EXPOSED ❌
  Attacks: UNPROTECTED ❌
  Visibility: NONE ❌

After SENTRIX:
  Your API: PROTECTED ✅
  Attacks: BLOCKED ✅
  Visibility: COMPLETE ✅
```

---

## 💡 REAL EXAMPLE: Your First Day

**8:00 AM**: Sign up to SENTRIX (2 minutes)  
**8:05 AM**: Update your `.env` file (1 minute)  
**8:10 AM**: Deploy to Vercel (5 minutes)  
**8:15 AM**: Test with curl (2 minutes)  
**8:20 AM**: ✅ **PROTECTED!**

**That Same Day**:
- 10:30 AM: SENTRIX blocks first SQL injection attack
- 2:45 PM: SENTRIX blocks DDoS attempt
- 5:00 PM: You receive daily security report

**You did nothing after deployment. Everything is automatic!** 🎉

---

## 🚨 IMPORTANT NOTES

### 1. You Don't Need to Change Your Backend!
Your backend at `api.x.com` **stays exactly the same**. No changes needed!

### 2. Your API Key is Your Password
- Store it in `.env` file (NOT in git!)
- Treat it like a password
- Can regenerate anytime from dashboard

### 3. Trial Period
- 14 days completely free
- No credit card required
- Full features enabled
- Cancel anytime

### 4. After Trial
- Auto-converts to paid ($149/month)
- Or downgrade to Free plan (10K requests)
- Email reminder 3 days before

---

## 📞 NEED HELP?

### Option 1: Use Nginx Proxy (Easiest)
- No client changes
- Just update nginx config
- Works immediately

### Option 2: Frontend Changes
- Simple: just 2 changes
- More control
- Easy to test

### Option 3: Contact Support
- Email: support@sentrix.io
- Live Chat: dashboard.sentrix.io
- Phone: Available for paid plans

---

## 🎉 YOU'RE DONE!

**Congratulations!** Your x.com API is now protected by SENTRIX.

**Sleep well** knowing that:
- ✅ Attacks are blocked automatically
- ✅ You get alerted to threats
- ✅ Everything is monitored 24/7
- ✅ No maintenance needed from you

**Welcome to SENTRIX!** 🛡️

---

*Questions? Email: support@sentrix.io*  
*Need help with integration? We can do it for you!*

