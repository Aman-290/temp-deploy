# Jarvis AI Backend - Production Deployment

Backend service for Jarvis AI Assistant, deployed on Google Cloud Run.

## 🚀 Quick Start

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for complete deployment instructions.

## 📦 What's Included

- **OAuth Server** (`run_server.py`): Handles Google OAuth for Gmail and Calendar
- **Voice Agent** (`run_agent.py`): LiveKit-powered voice assistant with Mem0 memory
- **Multi-user Support**: SQLite database for per-user token storage
- **Docker Configuration**: Production-ready Dockerfile with Python 3.12.9

## 🏗️ Architecture

```
┌─────────────────┐
│  Cloud Run      │
│  ┌───────────┐  │
│  │ OAuth     │  │ ← Port 8080 (public)
│  │ Server    │  │
│  └───────────┘  │
│  ┌───────────┐  │
│  │ LiveKit   │  │ ← Connects to LiveKit Cloud
│  │ Agent     │  │
│  └───────────┘  │
└─────────────────┘
```

## 🔑 Environment Variables

See `.env.cloudrun` for the complete list of required environment variables.

Key variables:
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
- `OPENAI_API_KEY`, `MEM0_API_KEY`
- `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REDIRECT_URI`
- `CALENDAR_CLIENT_ID`, `CALENDAR_CLIENT_SECRET`, `CALENDAR_REDIRECT_URI`

## 🔒 Security

- All API keys stored as Cloud Run environment variables
- OAuth 2.0 for Google services (Gmail, Calendar)
- Clerk authentication for user management
- Per-user data isolation with unique user IDs

## 📚 Documentation

- [Full Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [Environment Variables Template](./.env.cloudrun)

## 🛠️ Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your credentials

# Run OAuth server
python run_server.py

# Run LiveKit agent (in separate terminal)
python run_agent.py dev
```

## 📝 License

Proprietary
