import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token import Token, UserTrackedToken
from app.repositories.base import BaseRepository


class TokenRepository(BaseRepository[Token]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Token)

    async def get_by_contract(self, contract_address: str, chain: str = "ethereum") -> Token | None:
        result = await self._session.execute(
            select(Token).where(
                Token.contract_address == contract_address.lower(),
                Token.chain == chain,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_symbol(self, symbol: str, chain: str = "ethereum") -> list[Token]:
        result = await self._session.execute(
            select(Token).where(
                Token.symbol == symbol.upper(),
                Token.chain == chain,
            )
        )
        return list(result.scalars().all())

    async def get_user_tokens(self, user_id: uuid.UUID) -> list[Token]:
        result = await self._session.execute(
            select(Token)
            .join(UserTrackedToken, UserTrackedToken.token_id == Token.id)
            .where(UserTrackedToken.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_all_tracked_contracts(self, chain: str = "ethereum") -> list[str]:
        """Return all contract addresses being tracked by any user."""
        result = await self._session.execute(
            select(Token.contract_address)
            .join(UserTrackedToken, UserTrackedToken.token_id == Token.id)
            .where(Token.chain == chain)
            .distinct()
        )
        return list(result.scalars().all())

    async def add_user_tracking(
        self,
        user_id: uuid.UUID,
        token_id: uuid.UUID,
        threshold_usd: float | None = None,
    ) -> None:
        tracking = UserTrackedToken(
            user_id=user_id,
            token_id=token_id,
            threshold_usd=threshold_usd,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(tracking)
        await self._session.flush()

    async def remove_user_tracking(
        self, user_id: uuid.UUID, token_id: uuid.UUID
    ) -> bool:
        result = await self._session.execute(
            delete(UserTrackedToken).where(
                UserTrackedToken.user_id == user_id,
                UserTrackedToken.token_id == token_id,
            )
        )
        return result.rowcount > 0
