from fastapi import APIRouter, Depends

from app.core.security import get_current_user


router = APIRouter(prefix="/api/v1/auth")


@router.get("/me")
async def me(current_user=Depends(get_current_user)):
    return current_user