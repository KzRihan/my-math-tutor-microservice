"""
Main FastAPI application for Math Agent Base
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.routes import router


def create_app() -> FastAPI:
  """
  Create and configure FastAPI application

  Returns:
    Configured FastAPI app instance
  """
  app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=(
      "A Math Tutor Service using Ollama and Redis "
      "for session management"
    ),
  )

  # Add CORS middleware
  app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
  )

  # Include API v1 router with versioned prefix
  app.include_router(router, prefix="/api/v1", tags=["v1"])

  # Also include routes at root level for backward compatibility
  app.include_router(router, tags=["legacy"])

  # Root endpoint
  @app.get("/")
  async def root():
    return {
      "message": settings.API_TITLE,
      "version": settings.API_VERSION,
      "docs": "/docs"
    }

  return app


# Create app instance
app = create_app()
