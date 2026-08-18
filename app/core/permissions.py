from fastapi import Depends, HTTPException, status
from app.core.current_user import AuthenticatedUser, get_current_user


def require_roles(*allowed_roles: str):
    async def checker(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if not set(current_user.roles) & set(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this resource",
            )
        return current_user

    return checker