import uvicorn
import os
from app.server import app

if __name__ == "__main__":
    # Cloud Run sets PORT environment variable
    port = int(os.getenv("PORT", "8000"))
    
    print("\n" + "="*60)
    print("🤖 Jarvis OAuth Server Starting...")
    print("="*60)
    print(f"\n📍 Server will run on port: {port}")
    print(f"📧 Gmail auth: /gmail/auth")
    print(f"📅 Calendar auth: /calendar/auth")
    print("\n💡 Tip: Leave this server running while using the voice agent")
    print("="*60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
