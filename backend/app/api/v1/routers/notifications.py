from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.database.session import get_db_session
from app.models.user import User
from app.notifications.interfaces import ChannelType
from app.repositories.notification import NotificationSettingRepository

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationSettingResponse(BaseModel):
    model_config = {"from_attributes": True}
    channel: str
    is_enabled: bool
    config: dict


class UpsertNotificationRequest(BaseModel):
    channel: ChannelType
    is_enabled: bool = True
    config: dict = {}


@router.get("/settings", response_model=list[NotificationSettingResponse])
async def get_notification_settings(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = NotificationSettingRepository(session)
    return await repo.get_user_settings(current_user.id)


@router.put(
    "/settings",
    response_model=NotificationSettingResponse,
    status_code=status.HTTP_200_OK,
)
async def upsert_notification_setting(
    body: UpsertNotificationRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = NotificationSettingRepository(session)
    setting = await repo.upsert(
        user_id=current_user.id,
        channel=body.channel,
        config=body.config,
        is_enabled=body.is_enabled,
    )
    return setting
