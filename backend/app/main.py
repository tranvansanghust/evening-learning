"""
FastAPI application initialization and configuration.

This module sets up the FastAPI application with middleware, routes,
and health check endpoints.

Usage:
    To run the application locally with Uvicorn:

    ```bash
    # Install dependencies
    pip install -r requirements.txt

    # Set up environment variables (copy from .env.example)
    cp .env.example .env

    # Run development server with auto-reload
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

    # Or run production server
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    ```

    The application will be available at:
    - API: http://localhost:8000
    - Docs: http://localhost:8000/docs (Swagger UI)
    - ReDoc: http://localhost:8000/redoc
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings


# Initialize FastAPI application
app = FastAPI(
    title="Evening Learning - Backend",
    description="Intelligent learning system with Telegram bot and Claude API integration",
    version="0.1.0",
    debug=settings.debug,
)


# Configure CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "http://localhost",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """
    Health check endpoint for monitoring application status.

    Returns:
        dict: Status information with application uptime details

    This endpoint can be used by load balancers and monitoring systems
    to verify that the application is running and healthy.
    """
    return {
        "status": "healthy",
        "service": "evening-learning-backend",
        "version": "0.1.0",
    }


from app.routers import telegram, onboarding, learning, quiz, progress


def include_routers() -> None:
    """
    Include all API routers after they are created.

    This function includes routers from:
    - app.routers.onboarding: Onboarding flow endpoints
    - app.routers.learning: Learning flow endpoints
    - app.routers.quiz: Quiz and evaluation endpoints
    - app.routers.progress: Progress tracking endpoints
    - app.routers.telegram: Telegram webhook endpoint
    """
    # Include Onboarding router
    app.include_router(onboarding.router, prefix="/api/onboard", tags=["Onboarding"])

    # Include Learning router
    app.include_router(learning.router, prefix="/api/learn", tags=["Learning"])

    # Include Quiz router
    app.include_router(quiz.router, prefix="/api/quiz", tags=["Quiz"])

    # Include Progress router
    app.include_router(progress.router, prefix="/api", tags=["Progress"])

    # Include Telegram webhook router
    app.include_router(telegram.router, tags=["Telegram Webhook"])


# Include routers when this module is loaded
include_routers()


@app.on_event("startup")
async def startup_event() -> None:
    """
    Initialize resources on application startup.

    This is called once when the application starts, before accepting requests.
    """
    print(f"Starting Evening Learning Backend (Debug: {settings.debug})")
    print(f"Database: {settings.db_host}:{settings.db_port}/{settings.db_name}")

    # Log Telegram configuration status
    if settings.telegram_bot_token:
        print(f"Telegram Bot: Configured")
        print(f"Webhook URL: {settings.telegram_webhook_url or 'Not set'}")
    else:
        print("Telegram Bot: Not configured (TELEGRAM_BOT_TOKEN not set)")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Clean up resources on application shutdown.

    This is called once when the application is shutting down.
    """
    print("Shutting down Evening Learning Backend")
