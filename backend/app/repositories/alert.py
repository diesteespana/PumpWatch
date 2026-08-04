import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.repositories.base import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Alert)

    async def get_user_alerts(
        self, user_id: uuid.UUID, *, active_only: bool = False
    ) -> list[Alert]:
        stmt = select(Alert).where(Alert.user_id == user_id)
        if active_only:
            stmt = stmt.where(Alert.is_active.is_(True))
        stmt = stmt.order_by(Alert.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_alerts_for_event(
        self,
        event_type: str,
        wallet_address: str,
        token_contract: str,
        usd_value: float,
    ) -> list[Alert]:
        """
        Return all active alerts that match the given event parameters.

        Fetches all active alerts and applies in-Python filtering via
        Alert.matches_event() — simple and correct for current scale.

        At high user counts (10k+ alerts), replace with a DB-level filter
        using GIN indexes on the JSONB columns.
        """
        result = await self._session.execute(
            select(Alert).where(Alert.is_active.is_(True))
        )
        all_active = result.scalars().all()
        return [
            alert
            for alert in all_active
            if alert.matches_event(event_type, wallet_address, token_contract, usd_value)
        ]

    async def toggle_active(self, alert_id: uuid.UUID, is_active: bool) -> Alert | None:
        alert = await self.get_by_id(alert_id)
        if alert is None:
            return None
        return await self.update(alert, is_active=is_active)
