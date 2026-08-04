import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select, text
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

    async def count_recent(
        self,
        *,
        chain: str | None = None,
        event_type: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(OnChainEvent)
        if chain:
            stmt = stmt.where(OnChainEvent.blockchain == chain)
        if event_type:
            stmt = stmt.where(OnChainEvent.event_type == event_type)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_wallet_event_counts(self, address: str) -> dict[str, int]:
        """Return {event_type: count} for all events belonging to this address."""
        result = await self._session.execute(
            select(OnChainEvent.event_type, func.count().label("cnt"))
            .where(OnChainEvent.wallet_address == address.lower())
            .group_by(OnChainEvent.event_type)
        )
        return {row.event_type: row.cnt for row in result.all()}

    async def get_wallet_total_volume(self, address: str) -> float:
        result = await self._session.execute(
            select(func.coalesce(func.sum(OnChainEvent.usd_value), 0))
            .where(OnChainEvent.wallet_address == address.lower())
        )
        return float(result.scalar_one())

    async def get_wallet_first_last_seen(
        self, address: str
    ) -> tuple[datetime | None, datetime | None]:
        result = await self._session.execute(
            select(
                func.min(OnChainEvent.timestamp),
                func.max(OnChainEvent.timestamp),
            ).where(OnChainEvent.wallet_address == address.lower())
        )
        row = result.one()
        return row[0], row[1]

    async def get_volume_over_time(
        self, address: str, *, days: int = 30
    ) -> list[dict]:
        """Return daily volume for the past N days (ascending date order)."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        # Cast timestamp to date for grouping
        day_col = func.date_trunc("day", OnChainEvent.timestamp).label("day")
        result = await self._session.execute(
            select(day_col, func.sum(OnChainEvent.usd_value).label("volume"))
            .where(
                OnChainEvent.wallet_address == address.lower(),
                OnChainEvent.timestamp >= since,
            )
            .group_by(day_col)
            .order_by(day_col)
        )
        return [
            {"date": str(row.day.date()), "volume": float(row.volume)}
            for row in result.all()
        ]

    async def get_top_wallets_by_volume(
        self, *, limit: int = 50, chain: str = "ethereum"
    ) -> list[tuple[str, float, int]]:
        """Return (wallet_address, total_volume, event_count) sorted by volume desc."""
        result = await self._session.execute(
            select(
                OnChainEvent.wallet_address,
                func.sum(OnChainEvent.usd_value).label("total_volume"),
                func.count().label("event_count"),
            )
            .where(OnChainEvent.blockchain == chain)
            .group_by(OnChainEvent.wallet_address)
            .order_by(text("total_volume DESC"))
            .limit(limit)
        )
        return [(row.wallet_address, float(row.total_volume), row.event_count) for row in result.all()]

    async def get_wallet_top_tokens(self, address: str, *, limit: int = 5) -> list[dict]:
        """Return the tokens with highest total volume for this wallet."""
        result = await self._session.execute(
            select(
                OnChainEvent.token_symbol,
                OnChainEvent.token_contract,
                func.sum(OnChainEvent.usd_value).label("volume"),
                func.count().label("count"),
            )
            .where(OnChainEvent.wallet_address == address.lower())
            .group_by(OnChainEvent.token_symbol, OnChainEvent.token_contract)
            .order_by(text("volume DESC"))
            .limit(limit)
        )
        return [
            {
                "symbol": row.token_symbol,
                "contract": row.token_contract,
                "volume": float(row.volume),
                "count": row.count,
            }
            for row in result.all()
        ]
