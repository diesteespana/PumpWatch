from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.blockchain.address_registry import AddressRegistry
from app.core.exceptions import ConflictError, NotFoundError
from app.database.session import get_db_session
from app.models.user import User
from app.repositories.wallet import WalletRepository
from app.schemas.wallet import TrackWalletRequest, WalletResponse

router = APIRouter(prefix="/wallets", tags=["wallets"])

_registry = AddressRegistry()


@router.get("", response_model=list[WalletResponse])
async def list_wallets(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = WalletRepository(session)
    return await repo.get_user_wallets(current_user.id)


@router.post("", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def track_wallet(
    body: TrackWalletRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = WalletRepository(session)

    # Get or create the shared Wallet record
    wallet = await repo.get_by_address(body.address, body.chain)
    if wallet is None:
        label = _registry.get(body.address)
        wallet = await repo.create(
            address=body.address,
            chain=body.chain,
            label=body.custom_label or (label.name if label else ""),
            is_exchange=_registry.is_exchange(body.address),
            exchange_name=label.name if label and _registry.is_exchange(body.address) else None,
        )

    # Check if user already tracks this wallet
    existing = await repo.get_user_wallets(current_user.id)
    if any(w.id == wallet.id for w in existing):
        raise ConflictError(f"Already tracking wallet: {body.address}")

    await repo.add_user_tracking(
        user_id=current_user.id,
        wallet_id=wallet.id,
        custom_label=body.custom_label,
        threshold_usd=body.threshold_usd,
    )
    return wallet


@router.delete("/{address}", status_code=status.HTTP_204_NO_CONTENT)
async def untrack_wallet(
    address: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = WalletRepository(session)
    wallet = await repo.get_by_address(address.lower())
    if wallet is None:
        raise NotFoundError("Wallet", address)
    removed = await repo.remove_user_tracking(current_user.id, wallet.id)
    if not removed:
        raise NotFoundError("Tracked wallet", address)
