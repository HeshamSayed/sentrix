# 🎯 SENTRIX NEW HIERARCHY - Complete Demonstration

## ✅ NEW STRUCTURE IMPLEMENTED

### Hierarchy: Organization → Environment → Application

```
TODO App Inc (Organization)
├── Production (Environment)
│   ├── TODO App API (Application) - API Key: sentrix_live_xxxxx
│   └── TODO Web Frontend (Application) - API Key: sentrix_live_yyyyy
├── Staging (Environment)
│   ├── TODO App API Staging (Application) - API Key: sentrix_live_zzzzz
│   └── TODO Web Frontend Staging (Application) - API Key: sentrix_live_aaaaa
└── Development (Environment)
    └── TODO App API Dev (Application) - API Key: sentrix_live_bbbbb
```

Each application has its own **unique, secure API key**.

## 📊 Key Changes

### 1. Model Structure

**OLD** (Flat):
- Organization
- Application (directly under organization)

**NEW** (Hierarchical):
- Organization
  - Environment (Production, Staging, Development, etc.)
    - Application (each with unique API key)

### 2. Benefits

✅ **Better Organization**: Separate prod/staging/dev environments  
✅ **Secure**: Each app has its own API key  
✅ **Flexible**: Multiple apps per environment  
✅ **Scalable**: Easy to add new environments  
✅ **Quota Management**: Allocate quota at environment level  

## 🧪 Complete Testing Guide

### Step 1: Sign Up

```bash
curl -X POST http://localhost:8000/api/onboarding/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@todoapp.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "company_name": "TODO App Inc"
  }'
```

**Response:**
```json
{
  "message": "Account created successfully",
  "user": {
    "id": "...",
    "email": "owner@todoapp.com"
  },
  "token": "a969e830be8db123a2504a38ea306680a6ff24ba"
}
```

### Step 2: View Available Plans

```bash
curl http://localhost:8000/api/onboarding/plans/
```

### Step 3: Quick Start (Create Everything)

This creates:
- Organization
- Subscription
- Multiple Environments
- Multiple Applications (each with secure API key)

```bash
export TOKEN="YOUR_TOKEN_FROM_STEP_1"

curl -X POST http://localhost:8000/api/onboarding/quick_start/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_name": "TODO App Inc",
    "plan_type": "starter",
    "environments": [
      {
        "name": "Production",
        "environment_type": "production",
        "description": "Production environment for live traffic",
        "applications": [
          {
            "name": "TODO App API",
            "description": "Main TODO REST API",
            "base_url": "https://todo.com",
            "target_url": "https://api.todo.com",
            "framework": "Flask",
            "language": "Python"
          },
          {
            "name": "TODO Web Frontend",
            "description": "React web application",
            "base_url": "https://todo.com",
            "target_url": "https://todo.com",
            "framework": "React",
            "language": "JavaScript"
          }
        ]
      },
      {
        "name": "Staging",
        "environment_type": "staging",
        "description": "Staging environment for testing",
        "applications": [
          {
            "name": "TODO App API Staging",
            "description": "Staging API for testing",
            "base_url": "https://staging.todo.com",
            "target_url": "https://api-staging.todo.com"
          }
        ]
      },
      {
        "name": "Development",
        "environment_type": "development",
        "description": "Development environment",
        "applications": [
          {
            "name": "TODO App API Dev",
            "base_url": "http://localhost:5000",
            "target_url": "http://localhost:5000"
          }
        ]
      }
    ]
  }'
```

**Response:**
```json
{
  "message": "Organization setup completed successfully!",
  "organization": {
    "id": "...",
    "name": "TODO App Inc",
    "slug": "todo-app-inc"
  },
  "subscription": {
    "plan_type": "starter",
    "plan_name": "Starter",
    "status": "trial",
    "trial_end_date": "2025-11-15T...",
    "max_requests": 1000000
  },
  "environments": [
    {
      "id": "...",
      "name": "Production",
      "environment_type": "production",
      "total_applications": 2,
      "active_applications": 2,
      "allocated_quota": 333333
    },
    {
      "id": "...",
      "name": "Staging",
      "environment_type": "staging",
      "total_applications": 1,
      "active_applications": 1,
      "allocated_quota": 333333
    },
    {
      "id": "...",
      "name": "Development",
      "environment_type": "development",
      "total_applications": 1,
      "active_applications": 1,
      "allocated_quota": 333334
    }
  ],
  "applications": [
    {
      "id": "...",
      "name": "TODO App API",
      "api_key": "sentrix_live_Abc123Def456Ghi789Jkl012Mno345",
      "base_url": "https://todo.com",
      "target_url": "https://api.todo.com",
      "environment_name": "Production",
      "organization_name": "TODO App Inc",
      "allocated_quota": 166666,
      "is_active": true
    },
    {
      "id": "...",
      "name": "TODO Web Frontend",
      "api_key": "sentrix_live_Pqr678Stu901Vwx234Yza567Bcd890",
      "base_url": "https://todo.com",
      "target_url": "https://todo.com",
      "environment_name": "Production",
      "organization_name": "TODO App Inc",
      "allocated_quota": 166667,
      "is_active": true
    },
    // ... more applications
  ],
  "next_steps": [
    "1. Save your API keys securely",
    "2. Update your application to use SENTRIX Edge: http://your-sentrix-domain:8001",
    "3. Add X-SENTRIX-Key header with your API key",
    "4. Test your integration",
    "5. Monitor your dashboard for security insights"
  ]
}
```

### Step 4: Use Applications with SENTRIX Protection

Now each application has its own API key. Use them separately:

#### Production API:
```bash
export API_KEY_PROD="sentrix_live_Abc123Def456Ghi789Jkl012Mno345"

# Protected request to production API
curl http://localhost:8001/api/todos \
  -H "X-SENTRIX-Key: $API_KEY_PROD"
```

#### Production Frontend:
```bash
export API_KEY_FRONTEND="sentrix_live_Pqr678Stu901Vwx234Yza567Bcd890"

# Protected request to production frontend
curl http://localhost:8001/ \
  -H "X-SENTRIX-Key: $API_KEY_FRONTEND"
```

#### Staging API:
```bash
export API_KEY_STAGING="sentrix_live_Zzz999Xxx888Yyy777Www666Vvv555"

# Protected request to staging API
curl http://localhost:8001/api/todos \
  -H "X-SENTRIX-Key: $API_KEY_STAGING"
```

## 📈 Features

### 1. Environment-Level Management
- Set maintenance mode per environment
- Allocate quota per environment
- Configure max applications per environment

### 2. Application-Level Security
- Unique API key per application
- Individual rate limits
- Separate IP blocking/allowing
- Custom headers per application
- Webhook notifications per app

### 3. Quota Distribution
```
Organization Subscription: 1,000,000 requests/month
├── Production Environment: 333,333 requests
│   ├── TODO App API: 166,666 requests
│   └── TODO Web Frontend: 166,667 requests
├── Staging Environment: 333,333 requests
│   └── TODO App API Staging: 333,333 requests
└── Development Environment: 333,334 requests
    └── TODO App API Dev: 333,334 requests
```

## 🔐 Security Benefits

1. **Isolation**: Compromised staging key doesn't affect production
2. **Granular Control**: Different rate limits per application
3. **Easy Rotation**: Regenerate keys per application without affecting others
4. **Audit Trail**: Track usage per application
5. **Least Privilege**: Each app only gets access to its own resources

## 📊 Monitoring & Analytics

Each level provides metrics:

### Organization Level:
- Total requests across all environments
- Security events summary
- Subscription usage

### Environment Level:
- Requests per environment
- Active/inactive applications
- Environment-specific threats

### Application Level:
- Per-app request count
- API endpoint discovery
- Individual security events
- Response times

## 🔄 Key Rotation

Regenerate API key for a specific application:

```python
application = Application.objects.get(id='...')
new_key = application.regenerate_api_key()
print(f"New API Key: {new_key}")
```

## 📝 Database Schema

```sql
-- Organizations
CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    slug VARCHAR(255) UNIQUE,
    owner_id UUID REFERENCES users(id),
    ...
);

-- Environments (under organization)
CREATE TABLE environments (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id),
    name VARCHAR(100),
    environment_type VARCHAR(50), -- production, staging, development
    slug VARCHAR(100),
    max_applications INT,
    allocated_quota BIGINT,
    ...
    UNIQUE(organization_id, slug)
);

-- Applications (under environment, each with unique API key)
CREATE TABLE applications (
    id UUID PRIMARY KEY,
    environment_id UUID REFERENCES environments(id),
    name VARCHAR(255),
    slug VARCHAR(255),
    api_key VARCHAR(255) UNIQUE, -- Secure, unique per application
    base_url VARCHAR(500),
    target_url VARCHAR(500),
    allocated_quota BIGINT,
    rate_limit_per_minute INT,
    ...
    UNIQUE(environment_id, slug)
);
```

## 🎯 Real-World Example

**Company**: TaskMaster Inc  
**Use Case**: SaaS TODO application

**Structure**:
```
TaskMaster Inc
├── Production US
│   ├── API Server US-East
│   ├── API Server US-West
│   └── Web App CDN
├── Production EU
│   ├── API Server EU-West
│   └── Web App CDN
├── Staging
│   └── Full Stack Staging
└── Development
    ├── Backend Dev
    └── Frontend Dev
```

Each application gets its own API key, allowing:
- Geographic routing
- Independent scaling
- Separate monitoring
- Isolated security policies

## 🚀 Summary

✅ **Hierarchical Structure**: Org → Environment → Application  
✅ **Secure**: Unique API key per application  
✅ **Flexible**: Multiple environments & applications  
✅ **Scalable**: Easy to add new apps/environments  
✅ **Manageable**: Clear separation of concerns  
✅ **Production-Ready**: Full quota and security management  

---

**All files cleaned, structure updated, and ready for production!** 🎉

