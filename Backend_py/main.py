from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
import asyncio

from core.config import settings
from api.rfp_routes import router as rfp_router
from api.auth_routes import router as auth_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Bid Intelligence.ai API",
    description="Python Backend for RFP Analysis",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"Method: {request.method} Path: {request.url.path} Status: {response.status_code} Duration: {duration:.2f}s")
    return response

# Exception Handler for HTTPException (FastAPI's built-in)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions and format them for frontend"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error": exc.detail
        }
    )

# Exception Handler for general exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Handle cancellation errors gracefully (user stopped the request)
    if isinstance(exc, asyncio.CancelledError):
        logger.info(f"Request cancelled: {request.method} {request.url.path}")
        return JSONResponse(
            status_code=499,  # Client Closed Request
            content={"success": False, "error": "Request cancelled", "message": "Analysis was cancelled"}
        )
    
    logger.error(f"Global Exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc), "message": "An unexpected error occurred"}
    )

# Register Routes
app.include_router(rfp_router, prefix="/api/rfp", tags=["RFP"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

logger.info("✅ Routes registered:")
logger.info("   - /api/rfp")
logger.info("   - /api/auth (login, register, me, logout)")

@app.get("/")
async def root():
    return {
        "message": "Bid Intelligence.ai - RFP Analysis API (Python)",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "POST /api/rfp/analyze",
            "health": "GET /api/rfp/health"
        }
    }

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    try:
        # Test MongoDB connection
        from core.mongodb import get_mongodb
        db = get_mongodb()
        if db is not None:
            # Try to ping the database
            db.client.admin.command('ping')
            db_status = "connected (MongoDB)"
        else:
            db_status = "disconnected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "ok",
        "service": "Bid Intelligence.ai API",
        "database": db_status,
        "database_type": "MongoDB",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
