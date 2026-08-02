from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.blockchain.factory import create_blockchain_provider
from app.blockchain.interfaces import BlockchainProvider
from app.core.config import Settings, get_settings
from app.database.session import get_db_session

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    environment: str
    database: bool
    blockchain_provider: bool


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    from sqlalchemy import text
    from app.database.session import engine

    db_ok = False
    async with engine.begin() as conn:
        try:
            await conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            pass

    provider: BlockchainProvider = create_blockchain_provider()
    provider_ok = await provider.health_check()

    return HealthResponse(
        status="ok" if db_ok and provider_ok else "degraded",
        environment=settings.app_env,
        database=db_ok,
        blockchain_provider=provider_ok,
    )
