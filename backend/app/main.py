"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1 import router as api_v1_router
from app.db.engine import engine
from app.models import init_db


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Gig Platform API",
        description="AI Agent 接单撮合平台后端 API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(api_v1_router, prefix="/api/v1")

    # Health check
    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.on_event("startup")
    async def on_startup():
        init_db()

    return app


app = create_app()
