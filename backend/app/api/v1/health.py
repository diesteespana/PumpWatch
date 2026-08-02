from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from app.blockchain.factory import create_blockchain_provider
from app.blockchain.price_oracle import CoinGeckoPriceOracle
from app.core.config import Settings, get_settings
from app.database.redis import get_redis_client
from app.database.session import engine

router = APIRouter(tags=["health"])


class ComponentHealth(BaseModel):
    database: bool
    redis: bool
    blockchain_provider: bool
    price_oracle: bool


class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str
    components: ComponentHealth


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    # Database
    db_ok = False
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    # Redis
    redis_ok = False
    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        redis_ok = True
    except Exception:
        pass

    # Blockchain provider
    provider_ok = False
    try:
        provider = create_blockchain_provider()
        provider_ok = await provider.health_check()
    except Exception:
        pass

    # Price oracle
    oracle_ok = False
    try:
        oracle = CoinGeckoPriceOracle(redis_client=get_redis_client())
        oracle_ok = await oracle.health_check()
    except Exception:
        pass

    components = ComponentHealth(
        database=db_ok,
        redis=redis_ok,
        blockchain_provider=provider_ok,
        price_oracle=oracle_ok,
    )
    all_ok = all([db_ok, redis_ok, provider_ok, oracle_ok])

    return HealthResponse(
        status="ok" if all_ok else "degraded",
        environment=settings.app_env,
        version="0.1.0",
        components=components,
    )
