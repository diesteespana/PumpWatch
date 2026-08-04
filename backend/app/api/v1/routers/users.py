from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.database.session import get_db_session
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = UserRepository(session)
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return current_user
    if "username" in updates:
        if await repo.username_exists(updates["username"]):
            from app.core.exceptions import ConflictError
            raise ConflictError("Username already taken")
    updated = await repo.update(current_user, **updates)
    return updated


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    repo = UserRepository(session)
    await repo.update(current_user, is_active=False)
