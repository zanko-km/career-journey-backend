from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import bearer_scheme, decode_token
from app.models import User, Employee, EmployeeRole
from app.core.exceptions import APIException
from app.models.user import EmployeeRoleType


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "x-allowed-roles": [
                "EMPLOYEE",
                "MANAGER",
                "HRBP",
                "HR_MANAGER",
            ]
        }
    )

    id: int
    employee_id: int
    username: str
    full_name: str
    roles: list[EmployeeRoleType]


async def load_authenticated_user(
    auth_provider_id: str,
    db: AsyncSession,
) -> AuthenticatedUser:
    user = (
        await db.execute(
            select(User).where(User.auth_provider_id == auth_provider_id)
        )
    ).scalar_one_or_none()

    if user is None:
        raise APIException(
            code="UNAUTHORIZED",
            message="User not provisioned in system",
        )

    employee = await db.get(Employee, user.employee_id)

    extra_roles = (
        await db.execute(
            select(EmployeeRole.role).where(
                EmployeeRole.employee_id == employee.id
            )
        )
    ).scalars().all()

    return AuthenticatedUser(
        id=user.id,
        employee_id=employee.id,
        username=employee.username,
        full_name=employee.full_name,
        roles=[EmployeeRoleType.EMPLOYEE] + [EmployeeRoleType(role) for role in extra_roles],
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    payload = decode_token(credentials.credentials)
    return await load_authenticated_user(payload["sub"], db)