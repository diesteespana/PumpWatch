import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.wallet import UserTrackedWallet, Wallet
from app.repositories.base import BaseRepository


class WalletRepository(BaseRepository[Wallet]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Wallet)

    async def get_by_address(self, address: str, chain: str = "ethereum") -> Wallet | None:
        result = await self._session.execute(
            select(Wallet).where(
                Wallet.address == address.lower(),
                Wallet.chain == chain,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_wallets(self, user_id: uuid.UUID) -> list[Wallet]:
        result = await self._session.execute(
            select(Wallet)
            .join(UserTrackedWallet, UserTrackedWallet.wallet_id == Wallet.id)
            .where(UserTrackedWallet.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_all_tracked_addresses(self, chain: str = "ethereum") -> list[str]:
        """Return distinct addresses being tracked by any user — used by the scheduler."""
        result = await self._session.execute(
            select(Wallet.address).where(Wallet.chain == chain).distinct()
        )
        return list(result.scalars().all())

    async def add_user_tracking(
        self,
        user_id: uuid.UUID,
        wallet_id: uuid.UUID,
        custom_label: str | None = None,
        threshold_usd: float | None = None,
    ) -> UserTrackedWallet:
        from datetime import datetime, timezone

        assoc = UserTrackedWallet(
            user_id=user_id,
            wallet_id=wallet_id,
            custom_label=custom_label,
            threshold_usd=threshold_usd,
            created_at=datetime.now(tz=timezone.utc),
        )
        self._session.add(assoc)
        await self._session.flush()
        return assoc

    async def remove_user_tracking(self, user_id: uuid.UUID, wallet_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(UserTrackedWallet).where(
                UserTrackedWallet.user_id == user_id,
                UserTrackedWallet.wallet_id == wallet_id,
            )
        )
        assoc = result.scalar_one_or_none()
        if assoc is None:
            return False
        await self._session.delete(assoc)
        await self._session.flush()
        return True
