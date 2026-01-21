"""
Start the application server with MongoDB only
"""
import uvicorn
from core.config import settings
from main import app

if __name__ == "__main__":
    print("🚀 Starting Bid Intelligence.ai API Server (MongoDB Only)")
    print(f"   Port: {settings.PORT}")
    print(f"   Database: MongoDB")
    print(f"   MongoDB Connection: {settings.MONGODB_STRING[:50]}..." if settings.MONGODB_STRING else "   ⚠️ MongoDB connection string not configured")
    print("")
    
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT, log_level="info")

