import uuid
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import OnChainEvent
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[OnChainEvent]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OnChainEvent)

    async def get_recent(
        self,
        *,
        chain: str | None = None,
        event_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[OnChainEvent]:
        stmt = select(OnChainEvent).order_by(OnChainEvent.timestamp.desc())
        if chain:
            stmt = stmt.where(OnChainEvent.blockchain == chain)
        if event_type:
            stmt = stmt.where(OnChainEvent.event_type == event_type)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_wallet(
        self,
        wallet_address: str,
        *,
        since: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[OnChainEvent]:
        stmt = (
            select(OnChainEvent)
            .where(OnChainEvent.wallet_address == wallet_address.lower())
            .order_by(OnChainEvent.timestamp.desc())
        )
        if since:
            stmt = stmt.where(OnChainEvent.timestamp >= since)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_tx_hash(self, tx_hash: str) -> list[OnChainEvent]:
        result = await self._session.execute(
            select(OnChainEvent).where(OnChainEvent.tx_hash == tx_hash)
        )
        return list(result.scalars().all())

    async def tx_hash_exists(self, tx_hash: str, event_type: str) -> bool:
        """
        Prevent duplicate event persistence for the same tx + type combination.
        Called by the detection engine before inserting.
        """
        result = await self._session.execute(
            select(OnChainEvent.id).where(
                and_(
                    OnChainEvent.tx_hash == tx_hash,
                    OnChainEvent.event_type == event_type,
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_by_token(
        self,
        token_contract: str,
        *,
        min_usd_value: float = 0,
        page: int = 1,
        page_size: int = 20,
    ) -> list[OnChainEvent]:
        stmt = (
            select(OnChainEvent)
            .where(
                OnChainEvent.token_contract == token_contract.lower(),
                OnChainEvent.usd_value >= min_usd_value,
            )
            .order_by(OnChainEvent.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
