import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.routes import auth as auth_router
from app.routes import generate as generate_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiter (slowapi / Redis storage recommended for multi-process)
# ---------------------------------------------------------------------------
settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    storage_uri=settings.REDIS_URL,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s …", settings.APP_NAME)
    # Verify DB connectivity on startup (schema managed by Alembic)
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("PostgreSQL connection verified.")
    yield
    await engine.dispose()
    logger.info("Shutting down %s …", settings.APP_NAME)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    description="AI Image Generation API powered by Krea AI + Celery",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# ── Middleware ───────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router.router, prefix=settings.API_V1_STR)
app.include_router(generate_router.router, prefix=settings.API_V1_STR)


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/healthz", tags=["ops"])
async def healthz():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        logger.warning("DB health check failed: %s", exc)
        db_status = "error"
    return {"status": "ok", "db": db_status}


# ── Global exception handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
