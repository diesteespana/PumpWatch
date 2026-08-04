import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wallet_score import WalletScore
from app.repositories.base import BaseRepository


class WalletScoreRepository(BaseRepository[WalletScore]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WalletScore)

    async def get_by_wallet_id(self, wallet_id: uuid.UUID) -> WalletScore | None:
        result = await self._session.execute(
            select(WalletScore).where(WalletScore.wallet_id == wallet_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        wallet_id: uuid.UUID,
        score: float,
        trade_count: int,
        insights: list[str],
        win_rate: float | None = None,
    ) -> WalletScore:
        existing = await self.get_by_wallet_id(wallet_id)
        now = datetime.now(timezone.utc)
        if existing:
            return await self.update(
                existing,
                score=score,
                trade_count=trade_count,
                insights=insights,
                win_rate=win_rate,
                scored_at=now,
            )
        return await self.create(
            wallet_id=wallet_id,
            score=score,
            trade_count=trade_count,
            insights=insights,
            win_rate=win_rate,
            scored_at=now,
        )

    async def get_top_scored(self, *, limit: int = 50) -> list[WalletScore]:
        result = await self._session.execute(
            select(WalletScore)
            .order_by(WalletScore.score.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
