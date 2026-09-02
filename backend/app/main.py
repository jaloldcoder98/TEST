from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers

settings = get_settings()

app = FastAPI(
    title="GYM Platform API",
    version="0.1.0",
    description="Backend for the GYM web app, Telegram bot, AI coach, and food analyzer.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def root_health() -> dict:
    """Unversioned health check for container orchestration / load balancers."""
    return {"success": True, "status": "ok"}
