import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.exceptions import AuthorizationError, NotFoundError
from app.database.session import get_db_session
from app.models.user import User
from app.repositories.alert import AlertRepository
from app.schemas.alert import AlertCreate, AlertResponse, AlertUpdate

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    active_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = AlertRepository(session)
    return await repo.get_user_alerts(current_user.id, active_only=active_only)


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    body: AlertCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = AlertRepository(session)
    return await repo.create(
        user_id=current_user.id,
        name=body.name,
        event_types=[str(e) for e in body.event_types],
        wallet_addresses=body.wallet_addresses,
        token_contracts=body.token_contracts,
        min_usd_value=body.min_usd_value,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = AlertRepository(session)
    alert = await repo.get_by_id(alert_id)
    if alert is None:
        raise NotFoundError("Alert", str(alert_id))
    if alert.user_id != current_user.id:
        raise AuthorizationError("Not your alert")
    return alert


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: uuid.UUID,
    body: AlertUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = AlertRepository(session)
    alert = await repo.get_by_id(alert_id)
    if alert is None:
        raise NotFoundError("Alert", str(alert_id))
    if alert.user_id != current_user.id:
        raise AuthorizationError("Not your alert")
    updates = body.model_dump(exclude_none=True)
    if "event_types" in updates:
        updates["event_types"] = [str(e) for e in updates["event_types"]]
    return await repo.update(alert, **updates)


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = AlertRepository(session)
    alert = await repo.get_by_id(alert_id)
    if alert is None:
        raise NotFoundError("Alert", str(alert_id))
    if alert.user_id != current_user.id:
        raise AuthorizationError("Not your alert")
    await repo.delete(alert)
