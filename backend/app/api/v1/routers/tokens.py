from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.exceptions import ConflictError, NotFoundError
from app.database.session import get_db_session
from app.models.user import User
from app.repositories.token import TokenRepository
from app.schemas.token import TokenResponse, TrackTokenRequest

router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.get("", response_model=list[TokenResponse])
async def list_tokens(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = TokenRepository(session)
    return await repo.get_user_tokens(current_user.id)


@router.post("", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def track_token(
    body: TrackTokenRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = TokenRepository(session)

    token = await repo.get_by_contract(body.contract_address, body.chain)
    if token is None:
        token = await repo.create(
            contract_address=body.contract_address,
            chain=body.chain,
            symbol=body.symbol,
            name=body.name or body.symbol,
        )

    existing = await repo.get_user_tokens(current_user.id)
    if any(t.id == token.id for t in existing):
        raise ConflictError(f"Already tracking token: {body.contract_address}")

    await repo.add_user_tracking(
        user_id=current_user.id,
        token_id=token.id,
        threshold_usd=body.threshold_usd,
    )
    return token


@router.delete("/{contract_address}", status_code=status.HTTP_204_NO_CONTENT)
async def untrack_token(
    contract_address: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = TokenRepository(session)
    token = await repo.get_by_contract(contract_address.lower())
    if token is None:
        raise NotFoundError("Token", contract_address)
    removed = await repo.remove_user_tracking(current_user.id, token.id)
    if not removed:
        raise NotFoundError("Tracked token", contract_address)
