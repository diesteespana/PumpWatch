"""
Generic typed base repository.

All concrete repositories inherit this and get CRUD for free.
Domain-specific queries are added as typed methods on the subclass.

Why repository pattern (not just raw queries in services)?
- Services stay testable: swap the repository with a mock, no DB needed
- Query logic is centralised: no duplicated SQLAlchemy selects across services
- Future ORM migration (if ever) only touches repository files
"""
import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, id: uuid.UUID) -> ModelT | None:
        return await self._session.get(self._model, id)

    async def get_all(self, *, page: int = 1, page_size: int = 20) -> list[ModelT]:
        offset = (page - 1) * page_size
        result = await self._session.execute(
            select(self._model).offset(offset).limit(page_size)
        )
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> ModelT:
        instance = self._model(**kwargs)
        self._session.add(instance)
        await self._session.flush()  # populate server defaults (e.g. created_at)
        await self._session.refresh(instance)
        return instance

    async def update(self, instance: ModelT, **kwargs: Any) -> ModelT:
        for key, value in kwargs.items():
            setattr(instance, key, value)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self._session.delete(instance)
        await self._session.flush()

    async def count(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(self._model)
        )
        return result.scalar_one()

    async def exists(self, id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(func.count()).select_from(self._model).where(
                self._model.id == id  # type: ignore[attr-defined]
            )
        )
        return result.scalar_one() > 0
