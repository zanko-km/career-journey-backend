from fastapi import APIRouter, Depends, HTTPException, status, Response

from app.core.current_user import get_current_user, load_authenticated_user, AuthenticatedUser
from app.schemas.auth import LoginRequest
from app.services.auth import AuthService
from app.core.supabase import get_supabase
from supabase import Client
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.auth import AuthResponse, UserSummary
from app.core.security import bearer_scheme
from fastapi.security import HTTPAuthorizationCredentials
from app.schemas.auth import RefreshRequest
from app.schemas.errors import ErrorResponse


router = APIRouter(prefix="/auth")


def get_auth_service(
    supabase: Client = Depends(get_supabase),
) -> AuthService:
    return AuthService(supabase)

@router.get(
    "/me",
    response_model=AuthenticatedUser,
    openapi_extra={
        "x-allowed-roles": [
            "EMPLOYEE",
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        ]
    },
    responses={
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        }
    },
    )
async def me(current_user: AuthenticatedUser =Depends(get_current_user)):
    return current_user

@router.post(
    "/login",
    response_model=AuthResponse,
    responses={
        401: {
                "description": "Unauthorized",
                "model": ErrorResponse,
            },
            422: {
                "description": "Validation Error",
                "model": ErrorResponse,
            },
        },
             )
async def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
):
    response = auth_service.login(
        username=payload.username,
        password=payload.password.get_secret_value(),
    )

    supabase_user_id = response.user.id
    authed_user = await load_authenticated_user(str(supabase_user_id), db)

    return AuthResponse(
        accessToken=response.session.access_token,
        refreshToken=response.session.refresh_token,
        expiresIn=response.session.expires_in,
        user=UserSummary(
            id=authed_user.id,
            employeeId=authed_user.employee_id,
            username=authed_user.username,
            fullName=authed_user.full_name,
            roles=authed_user.roles,
        ),
    )
    
@router.post("/refresh", response_model=AuthResponse,
             responses={
                 401: {
                    "description": "Unauthorized",
                    "model": ErrorResponse,
                 },
                 422: {
                    "description": "Unauthorized",
                    "model": ErrorResponse,
                 }
             })
async def refresh(
    payload: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
):
    try:
        response = auth_service.refresh(payload.refreshToken)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    authed_user = await load_authenticated_user(str(response.user.id), db)

    return AuthResponse(
        accessToken=response.session.access_token,
        refreshToken=response.session.refresh_token,
        expiresIn=response.session.expires_in,
        user=UserSummary(
            id=authed_user.employee_id,
            employeeId=authed_user.employee_id,
            username=authed_user.username,
            fullName=authed_user.full_name,
            roles=authed_user.roles,
        ),
    )

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        }
    },
)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
):
    auth_service.logout(credentials.credentials)

    return Response(status_code=status.HTTP_204_NO_CONTENT)