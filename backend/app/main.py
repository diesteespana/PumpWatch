from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.health import router as health_router
from app.api.v1.routers.alerts import router as alerts_router
from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.events import router as events_router
from app.api.v1.routers.analytics import router as analytics_router
from app.api.v1.routers.notifications import router as notifications_router
from app.api.v1.routers.paper_trading import router as paper_trading_router
from app.api.v1.routers.strategy import router as strategy_router
from app.api.v1.routers.tokens import router as tokens_router
from app.api.v1.routers.users import router as users_router
from app.api.v1.routers.wallets import router as wallets_router
from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    PumpWatchError,
    RateLimitedError,
    ValidationError,
)
from app.core.logging import configure_logging, get_logger
from app.core.middleware import AuditMiddleware

settings = get_settings()
configure_logging(debug=settings.app_debug)
logger = get_logger(__name__)

_API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("pumpwatch_startup", environment=settings.app_env)
    from app.scheduler import start_scheduler, stop_scheduler
    await start_scheduler()
    yield
    await stop_scheduler()
    from app.database.redis import get_redis_client
    await get_redis_client().aclose()
    logger.info("pumpwatch_shutdown")


app = FastAPI(
    title="PumpWatch API",
    description="On-chain analytics and whale tracking — pumpwat.ch",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── Middleware (order matters: outermost = first to handle request) ───────────
app.add_middleware(AuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────────────────────
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


@app.exception_handler(AuthenticationError)
async def auth_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(exc)})


@app.exception_handler(AuthorizationError)
async def authz_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})


@app.exception_handler(RateLimitedError)
async def rate_limit_handler(request: Request, exc: RateLimitedError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS, content={"detail": str(exc)}
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": str(exc)}
    )


@app.exception_handler(PumpWatchError)
async def domain_error_handler(request: Request, exc: PumpWatchError) -> JSONResponse:
    logger.error("unhandled_domain_error", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(auth_router, prefix=_API_PREFIX)
app.include_router(users_router, prefix=_API_PREFIX)
app.include_router(wallets_router, prefix=_API_PREFIX)
app.include_router(alerts_router, prefix=_API_PREFIX)
app.include_router(events_router, prefix=_API_PREFIX)
app.include_router(analytics_router, prefix=_API_PREFIX)
app.include_router(tokens_router, prefix=_API_PREFIX)
app.include_router(paper_trading_router, prefix=_API_PREFIX)
app.include_router(strategy_router, prefix=_API_PREFIX)
app.include_router(notifications_router, prefix=_API_PREFIX)
