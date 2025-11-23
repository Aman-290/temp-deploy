# Jarvis Backend - GCP Cloud Run Deployment Guide

## 📋 Prerequisites
- Google Cloud Platform account
- Docker installed locally
- Git installed
- gcloud CLI installed ([Install guide](https://cloud.google.com/sdk/docs/install))

## 🔑 Step 1: Get Google OAuth Credentials

### Navigate to Google Cloud Console
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Navigate to: **APIs & Services > Credentials**

### Create OAuth 2.0 Client ID
1. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
2. If prompted, configure the OAuth consent screen:
   - User Type: **External**
   - App name: **Jarvis AI Assistant**
   - User support email: Your email
   - Developer contact: Your email
   - Add scopes: Gmail and Calendar APIs
   - Add test users if in testing mode

3. Back in Credentials, create OAuth client ID:
   - Application type: **Web application**
   - Name: **Jarvis Backend**
   
4. **Authorized redirect URIs** - Add these (replace with your actual Cloud Run URL):
   ```
   https://your-service-name-abc123.run.app/gmail/callback
   https://your-service-name-abc123.run.app/calendar/callback
   http://localhost:8000/gmail/callback
   http://localhost:8000/calendar/callback
   ```

5. Click **Create** and save:
   - **Client ID** (e.g., `123456789-abc.apps.googleusercontent.com`)
   - **Client secret** (e.g., `GOCSPX-abc123xyz`)

### Enable Required APIs
Navigate to **APIs & Services > Library** and enable:
- Gmail API
- Google Calendar API

## 🚀 Step 2: Prepare for Deployment

### Update Backend Code
Your backend is already configured! The key changes made:
- ✅ `run_server.py` now uses `PORT` environment variable
- ✅ `Dockerfile` uses Python 3.12.9
- ✅ `start.sh` runs both server and agent
- ✅ SQLite database for multi-user support

### Test Docker Build Locally (Optional but Recommended)
```bash
cd backend
docker build -t jarvis-backend .
docker run -p 8000:8000 --env-file .env jarvis-backend
```

## 🔧 Step 3: Deploy to Cloud Run

### Authenticate with Google Cloud
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Build and Push to Cloud Run
```bash
cd backend

# Build and deploy in one command
gcloud run deploy jarvis-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --min-instances 0 \
  --max-instances 10
```

Cloud Run will output a service URL like:
```
https://jarvis-backend-abc123-uc.a.run.app
```

### Set Environment Variables in Cloud Run
After deployment, add environment variables:

```bash
gcloud run services update jarvis-backend \
  --region us-central1 \
  --update-env-vars \
LIVEKIT_URL=wss://your-project.livekit.cloud,\
LIVEKIT_API_KEY=your_key,\
LIVEKIT_API_SECRET=your_secret,\
OPENAI_API_KEY=sk-...,\
MEM0_API_KEY=your_mem0_key,\
GMAIL_CLIENT_ID=123456789-abc.apps.googleusercontent.com,\
GMAIL_CLIENT_SECRET=GOCSPX-abc123,\
GMAIL_REDIRECT_URI=https://jarvis-backend-abc123-uc.a.run.app/gmail/callback,\
CALENDAR_CLIENT_ID=123456789-abc.apps.googleusercontent.com,\
CALENDAR_CLIENT_SECRET=GOCSPX-abc123,\
CALENDAR_REDIRECT_URI=https://jarvis-backend-abc123-uc.a.run.app/calendar/callback,\
AUTH_SERVER_URL=https://jarvis-backend-abc123-uc.a.run.app,\
USER_TIMEZONE=America/Los_Angeles
```

Or set them via Cloud Console:
1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Click on your service
3. Click **"EDIT & DEPLOY NEW REVISION"**
4. Go to **"VARIABLES & SECRETS"** tab
5. Add each environment variable
6. Click **"DEPLOY"**

## 🔄 Step 4: Update OAuth Redirect URIs

1. Go back to [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials)
2. Click on your OAuth 2.0 Client ID
3. Under **"Authorized redirect URIs"**, add:
   ```
   https://jarvis-backend-abc123-uc.a.run.app/gmail/callback
   https://jarvis-backend-abc123-uc.a.run.app/calendar/callback
   ```
4. Save

## 🔍 Step 5: Update Frontend

Update your frontend's `Integrations.tsx` component to use the Cloud Run URL:

```typescript
const BACKEND_URL = "https://jarvis-backend-abc123-uc.a.run.app";

const fetchStatus = async () => {
  const res = await fetch(`${BACKEND_URL}/auth/status?user_id=${userId}`);
  // ...
};
```

Also update `server.py` CORS settings to allow your frontend domain.

## 📦 Step 6: Push to Deployment Repository

```bash
cd backend

# Initialize git if not already
git init

# Add deployment remote
git remote add deploy https://github.com/Jarvis-v-1/backend-for-deploying.git

# Add all files
git add .

# Commit
git commit -m "Initial deployment setup for Cloud Run"

# Push
git push -u deploy main
```

## 🧪 Step 7: Test the Deployment

1. **Check service health:**
   ```bash
   curl https://jarvis-backend-abc123-uc.a.run.app/
   ```

2. **Test OAuth status endpoint:**
   ```bash
   curl "https://jarvis-backend-abc123-uc.a.run.app/auth/status?user_id=test"
   ```

3. **Test Gmail OAuth flow:**
   - Visit: `https://jarvis-backend-abc123-uc.a.run.app/gmail/auth?user_id=test_user`
   - Should redirect to Google login

4. **Check Cloud Run logs:**
   ```bash
   gcloud run services logs read jarvis-backend --region us-central1
   ```

## 🔐 Security Notes

1. **Service Account**: Cloud Run automatically creates a service account
2. **IAM**: The service is set to `--allow-unauthenticated` so users can access OAuth endpoints
3. **API Keys**: All sensitive keys are stored as environment variables, never in code
4. **HTTPS**: Cloud Run automatically provides HTTPS

## 💰 Cost Optimization

- **Minimum instances**: Set to 0 (scales to zero when not in use)
- **Maximum instances**: Set to 10 (adjust based on usage)
- **Memory**: 2GB (reduce if not using large models)
- **CPU**: 2 (reduce to 1 if sufficient)

## 🆘 Troubleshooting

### Container fails to start
```bash
# View logs
gcloud run services logs read jarvis-backend --region us-central1 --limit 50

# Check service details
gcloud run services describe jarvis-backend --region us-central1
```

### OAuth redirect errors
- Verify redirect URIs exactly match in Google Console
- Check environment variables are set correctly
- Ensure CORS is configured properly

### Database issues
- SQLite database is ephemeral in Cloud Run (resets on deploy)
- For production, consider Cloud SQL or Firestore for persistent storage

## 📝 Useful Commands

```bash
# Update service with new code
gcloud run deploy jarvis-backend --source .

# View service URL
gcloud run services describe jarvis-backend --format="value(status.url)"

# Delete service
gcloud run services delete jarvis-backend --region us-central1
```

## 🎉 Success!

Your Jarvis backend is now running on Google Cloud Run! The OAuth server is publicly accessible for authentication while your LiveKit agent connects securely to LiveKit Cloud.
