from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.base import engine, Base
from app.api import auth, projects, videos, ai_generation, workflow, social_accounts, oauth, publishing, metrics, files, template
from app.core.scheduler import start_scheduler, shutdown_scheduler
import os
import logging
import logging.config

# Configure logging with timestamps (including uvicorn)
LOG_FORMAT = "%(asctime)s.%(msecs)03d | %(levelname)s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": LOG_FORMAT,
            "datefmt": LOG_DATE_FORMAT,
        },
    },
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stderr",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["default"],
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
    },
})

# Create database tables
Base.metadata.create_all(bind=engine)

# Create data directories
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.GENERATED_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
    redirect_slashes=False
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)  # auth router already has prefix="/api/auth"
app.include_router(auth.workspaces_router)  # workspaces router with prefix="/api/workspaces"
app.include_router(oauth.router, prefix="/api/oauth", tags=["oauth"])
app.include_router(social_accounts.router, prefix="/api/social-accounts", tags=["social-accounts"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(videos.router, prefix="/api/videos", tags=["videos"])
app.include_router(ai_generation.router, prefix="/api/ai", tags=["ai"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["workflow"])
app.include_router(publishing.router, prefix="/api/publish", tags=["publish"])
app.include_router(metrics.router, prefix="/api", tags=["metrics"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(template.router, prefix="/api", tags=["template"])


@app.get("/")
async def root():
    return {
        "message": "REGGY API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "healthy"}
