# Cloud Run Deployment via GitHub - Step-by-Step Guide

This guide walks you through deploying your Jarvis backend to Google Cloud Run directly from GitHub.

## 📋 Prerequisites Checklist

- [x] Code pushed to: https://github.com/Jarvis-v-1/backend-for-deploying
- [ ] Google Cloud Platform account
- [ ] GCP Project created
- [ ] Billing enabled on GCP project

---

## 🚀 Part 1: Deploy from GitHub to Cloud Run

### Step 1: Go to Cloud Run Console

1. Open: https://console.cloud.google.com/run
2. **Select your project** from the dropdown at the top
3. Click **"CREATE SERVICE"** button

### Step 2: Configure Source

**Container Image URL Section:**
1. Click **"Continuously deploy from a repository (source or function)"**
2. Click **"SET UP WITH CLOUD BUILD"**

**Set Up Cloud Build:**
1. **Repository Provider**: Select **GitHub**
2. Click **"AUTHENTICATE"** and sign in to GitHub
3. **Install Google Cloud Build** on your repository
4. Select repository: **`Jarvis-v-1/backend-for-deploying`**
5. **Branch**: `^main$` (regex pattern)
6. **Build Type**: Select **"Dockerfile"**
7. **Source Location**: `/Dockerfile` (path to Dockerfile)
8. Click **"SAVE"**

### Step 3: Configure Service Settings

**Service Settings:**
- **Service name**: `jarvis-backend` (you choose this - remember it!)
- **Region**: `us-central1` (or your preferred region)
- **CPU allocation**: "CPU is always allocated"
- **Minimum instances**: `0` (saves money)
- **Maximum instances**: `10`

**Container Settings:**
- **Container port**: `8000` (very important!)
- **Memory**: `2 GiB`
- **CPU**: `2`
- **Request timeout**: `3600` (1 hour)
- **Maximum concurrent requests**: `80`

**Authentication:**
- Select **"Allow unauthenticated invocations"** (required for OAuth)

Click **"CREATE"** at the bottom

### Step 4: Wait for Build

- Initial build takes 5-10 minutes
- You'll see build logs in real-time
- Once complete, you'll see: ✅ **Service URL** (this is your service name!)

**Example Service URL:**
```
https://jarvis-backend-abc123xyz-uc.a.run.app
```

**Your Service Name Components:**
- **Service name**: `jarvis-backend` (what you chose)
- **Full URL**: The complete URL shown above
- **Region code**: `uc` (us-central1), `uw` (us-west1), etc.

---

## 🔧 Part 2: Add Environment Variables

### Method 1: Via Cloud Run Console (Recommended for Beginners)

1. Go to: https://console.cloud.google.com/run
2. Click on your service: **`jarvis-backend`**
3. Click **"EDIT & DEPLOY NEW REVISION"** at the top
4. Scroll down to **"VARIABLES & SECRETS"** section
5. Click **"ADD VARIABLE"** for each variable below

**Add These Variables One by One:**

| Variable Name | Example Value | Where to Get It |
|--------------|---------------|-----------------|
| `LIVEKIT_URL` | `wss://your-project.livekit.cloud` | LiveKit Dashboard |
| `LIVEKIT_API_KEY` | `APIxxxxx` | LiveKit Dashboard → Settings |
| `LIVEKIT_API_SECRET` | `secretxxxxx` | LiveKit Dashboard → Settings |
| `OPENAI_API_KEY` | `sk-proj-xxxxx` | OpenAI Platform → API Keys |
| `MEM0_API_KEY` | `m0-xxxxx` | Mem0 Dashboard |
| `GMAIL_CLIENT_ID` | `123456-abc.apps.googleusercontent.com` | See Part 3 below |
| `GMAIL_CLIENT_SECRET` | `GOCSPX-xxxxx` | See Part 3 below |
| `GMAIL_REDIRECT_URI` | `https://jarvis-backend-abc123xyz-uc.a.run.app/gmail/callback` | Use YOUR service URL |
| `CALENDAR_CLIENT_ID` | Same as Gmail Client ID | See Part 3 below |
| `CALENDAR_CLIENT_SECRET` | Same as Gmail Client Secret | See Part 3 below |
| `CALENDAR_REDIRECT_URI` | `https://jarvis-backend-abc123xyz-uc.a.run.app/calendar/callback` | Use YOUR service URL |
| `AUTH_SERVER_URL` | `https://jarvis-backend-abc123xyz-uc.a.run.app` | Use YOUR service URL |
| `USER_TIMEZONE` | `America/Los_Angeles` | Your timezone |

6. After adding all variables, click **"DEPLOY"** at the bottom
7. Wait 2-3 minutes for redeployment

### Method 2: Via gcloud Command (Advanced)

```bash
gcloud run services update jarvis-backend \
  --region us-central1 \
  --update-env-vars \
LIVEKIT_URL=wss://your-project.livekit.cloud,\
LIVEKIT_API_KEY=your_key,\
LIVEKIT_API_SECRET=your_secret,\
OPENAI_API_KEY=sk-...,\
MEM0_API_KEY=your_mem0_key,\
GMAIL_CLIENT_ID=123456-abc.apps.googleusercontent.com,\
GMAIL_CLIENT_SECRET=GOCSPX-abc123,\
GMAIL_REDIRECT_URI=https://jarvis-backend-abc123-uc.a.run.app/gmail/callback,\
CALENDAR_CLIENT_ID=123456-abc.apps.googleusercontent.com,\
CALENDAR_CLIENT_SECRET=GOCSPX-abc123,\
CALENDAR_REDIRECT_URI=https://jarvis-backend-abc123-uc.a.run.app/calendar/callback,\
AUTH_SERVER_URL=https://jarvis-backend-abc123-uc.a.run.app,\
USER_TIMEZONE=America/Los_Angeles
```

---

## 🔑 Part 3: Get Google OAuth Credentials

### Step 1: Go to Google Cloud Console Credentials

1. Open: https://console.cloud.google.com/apis/credentials
2. **Make sure you're in the SAME project** as your Cloud Run service
3. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**

### Step 2: Configure OAuth Consent Screen (First Time Only)

If you haven't set up the consent screen:
1. Click **"CONFIGURE CONSENT SCREEN"**
2. **User Type**: Select **"External"** → **"CREATE"**
3. Fill in:
   - **App name**: `Jarvis AI Assistant`
   - **User support email**: Your email
   - **Developer contact**: Your email
4. Click **"SAVE AND CONTINUE"**
5. **Scopes**: Click **"ADD OR REMOVE SCOPES"**
   - Search for: `Gmail API`
   - Select: `https://www.googleapis.com/auth/gmail.readonly`
   - Select: `https://www.googleapis.com/auth/gmail.send`
   - Select: `https://www.googleapis.com/auth/gmail.compose`
   - Search for: `Google Calendar API`
   - Select: `https://www.googleapis.com/auth/calendar`
   - Select: `https://www.googleapis.com/auth/calendar.events`
   - Click **"UPDATE"**
6. Click **"SAVE AND CONTINUE"**
7. **Test users**: Add your email (and any other testers)
8. Click **"SAVE AND CONTINUE"** → **"BACK TO DASHBOARD"**

### Step 3: Create OAuth Client ID

1. Back in: https://console.cloud.google.com/apis/credentials
2. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. **Application type**: Select **"Web application"**
4. **Name**: `Jarvis Backend OAuth`

**Authorized redirect URIs** - Add BOTH:
```
https://jarvis-backend-abc123xyz-uc.a.run.app/gmail/callback
https://jarvis-backend-abc123xyz-uc.a.run.app/calendar/callback
```
*(Replace with YOUR actual Cloud Run service URL!)*

5. Click **"CREATE"**

### Step 4: Save Your Credentials

You'll see a popup with:
- **Client ID**: `123456789-abc123.apps.googleusercontent.com`
- **Client secret**: `GOCSPX-abc123xyz`

**Copy these now!** You'll need them for environment variables.

### Step 5: Enable Required APIs

Go to: https://console.cloud.google.com/apis/library

Search and enable:
- **Gmail API** → Click **"ENABLE"**
- **Google Calendar API** → Click **"ENABLE"**

---

## 📍 Part 4: Finding Your Service Name & URL

### Where to Find Service Name

**Option 1: Cloud Run Console**
1. Go to: https://console.cloud.google.com/run
2. You'll see your service listed with:
   - **Name**: `jarvis-backend` (your service name)
   - **URL**: `https://jarvis-backend-abc123xyz-uc.a.run.app` (full service URL)
   - **Region**: `us-central1` (or your chosen region)

**Option 2: After Deployment Success**
- Look for the green checkmark and **"Service URL"**
- This is your public endpoint

**Option 3: Via gcloud Command**
```bash
gcloud run services list --region us-central1
```

### Understanding Your Service URL

Your service URL format:
```
https://[service-name]-[random-hash]-[region-code].a.run.app
```

Example breakdown:
- `jarvis-backend` = Your chosen service name
- `abc123xyz` = Random hash (Cloud Run generates this)
- `uc` = Region code (us-central1)
- `.a.run.app` = Cloud Run domain

---

## ✅ Part 5: Verify Deployment

### Test 1: Check Service Health
```bash
curl https://your-service-url.run.app/
```
Expected response: `{"status": "running", "message": "Jarvis OAuth Server"}`

### Test 2: Check Auth Status Endpoint
```bash
curl "https://your-service-url.run.app/auth/status?user_id=test"
```
Expected response: `{"gmail": false, "calendar": false}`

### Test 3: Test OAuth Flow
1. Open in browser: `https://your-service-url.run.app/gmail/auth?user_id=test`
2. Should redirect to Google login
3. After authorization, should redirect back successfully

### Test 4: Check Cloud Run Logs
1. Go to: https://console.cloud.google.com/run
2. Click on **`jarvis-backend`**
3. Click **"LOGS"** tab
4. Look for:
   - `🤖 Jarvis OAuth Server Starting...`
   - No error messages

---

## 🔄 Part 6: Update Your Frontend

Update `Integrations.tsx` to use your Cloud Run URL:

```typescript
const BACKEND_URL = "https://jarvis-backend-abc123xyz-uc.a.run.app";

const fetchStatus = async () => {
  if (!userId) return;
  try {
    const res = await fetch(`${BACKEND_URL}/auth/status?user_id=${userId}`);
    const data = await res.json();
    setStatus(data);
  } catch (error) {
    console.error("Failed to fetch integration status", error);
  }
};

const handleConnect = (service: "gmail" | "calendar") => {
  if (!userId) return;
  window.location.href = `${BACKEND_URL}/${service}/auth?user_id=${userId}`;
};
```

Also update `server.py` CORS to allow your frontend:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://your-frontend-domain.com"  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🔁 Future Updates

Whenever you push to GitHub main branch:
1. Cloud Run **automatically rebuilds** and deploys
2. Takes ~5 minutes
3. Zero downtime deployment
4. Environment variables persist across deployments

---

## 🎉 You're Done!

Your backend is now live on Google Cloud Run with:
- ✅ Automatic HTTPS
- ✅ Auto-scaling (0 to 10 instances)
- ✅ GitHub auto-deployment
- ✅ Google OAuth integration
- ✅ Multi-user support

**Your Service URL**: `https://jarvis-backend-abc123xyz-uc.a.run.app`

Test it now by visiting: `https://your-url/auth/status?user_id=test`
