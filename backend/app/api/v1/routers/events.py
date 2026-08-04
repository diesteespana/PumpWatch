from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.database.session import get_db_session
from app.models.user import User
from app.repositories.event import EventRepository
from app.schemas.alert import PaginatedResponse
from app.schemas.event import OnChainEventResponse

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=PaginatedResponse)
async def list_events(
    chain: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    wallet_address: str | None = Query(default=None),
    token_contract: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = EventRepository(session)

    if wallet_address:
        items = await repo.get_by_wallet(
            wallet_address.lower(), page=page, page_size=page_size
        )
    elif token_contract:
        items = await repo.get_by_token(
            token_contract.lower(), page=page, page_size=page_size
        )
    else:
        items = await repo.get_recent(
            chain=chain, event_type=event_type, page=page, page_size=page_size
        )

    total = await repo.count()
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        has_next=len(items) == page_size,
        items=[OnChainEventResponse.model_validate(e) for e in items],
    )


@router.get("/{tx_hash}", response_model=list[OnChainEventResponse])
async def get_events_by_tx(
    tx_hash: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = EventRepository(session)
    return await repo.get_by_tx_hash(tx_hash)
