from dataclasses import dataclass, field
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import bearer_scheme, decode_token
from app.models import User, Employee, EmployeeRole


@dataclass
class AuthenticatedUser:
    employee_id: int
    username: str
    full_name: str
    roles: list[str] = field(default_factory=list)


async def load_authenticated_user(auth_provider_id: str, db: AsyncSession) -> AuthenticatedUser:
    user = (
        await db.execute(select(User).where(User.auth_provider_id == auth_provider_id))
    ).scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not provisioned in system",
        )

    employee = await db.get(Employee, user.employee_id)

    extra_roles = (
        await db.execute(
            select(EmployeeRole.role).where(EmployeeRole.employee_id == employee.id)
        )
    ).scalars().all()

    return AuthenticatedUser(
        employee_id=employee.id,
        username=employee.username,
        full_name=employee.full_name,
        roles=["EMPLOYEE"] + list(extra_roles),
    )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    payload = decode_token(credentials.credentials)
    return await load_authenticated_user(payload["sub"], db)