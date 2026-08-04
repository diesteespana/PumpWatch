from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import AuthService
from app.database.redis import get_redis_client
from app.database.session import get_db_session
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    return AuthService(
        user_repo=UserRepository(session),
        redis_client=get_redis_client(),
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, svc: AuthService = Depends(_auth_service)):
    user = await svc.register(
        email=body.email,
        username=body.username,
        password=body.password,
    )
    return user


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, svc: AuthService = Depends(_auth_service)):
    access, refresh = await svc.login(email=body.email, password=body.password)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(body: RefreshRequest, svc: AuthService = Depends(_auth_service)):
    access, refresh = await svc.refresh(body.refresh_token)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest, svc: AuthService = Depends(_auth_service)):
    await svc.logout(body.refresh_token)
