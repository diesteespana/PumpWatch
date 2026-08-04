import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationSetting
from app.repositories.base import BaseRepository


class NotificationSettingRepository(BaseRepository[NotificationSetting]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, NotificationSetting)

    async def get_user_settings(self, user_id: uuid.UUID) -> list[NotificationSetting]:
        result = await self._session.execute(
            select(NotificationSetting).where(
                NotificationSetting.user_id == user_id,
                NotificationSetting.is_enabled.is_(True),
            )
        )
        return list(result.scalars().all())

    async def get_by_channel(
        self, user_id: uuid.UUID, channel: str
    ) -> NotificationSetting | None:
        result = await self._session.execute(
            select(NotificationSetting).where(
                NotificationSetting.user_id == user_id,
                NotificationSetting.channel == channel,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: uuid.UUID,
        channel: str,
        config: dict,
        is_enabled: bool = True,
    ) -> NotificationSetting:
        existing = await self.get_by_channel(user_id, channel)
        if existing:
            return await self.update(existing, config=config, is_enabled=is_enabled)
        return await self.create(
            user_id=user_id,
            channel=channel,
            config=config,
            is_enabled=is_enabled,
        )
