import pytest
from fastapi import FastAPI, Depends
from httpx import ASGITransport, AsyncClient

from app.core.permissions import require_roles
from app.core.current_user import AuthenticatedUser, get_current_user


@pytest.mark.asyncio
async def test_require_roles_blocks_unauthorized_role():
    app = FastAPI()

    @app.get("/protected")
    async def protected(user=Depends(require_roles("HRBP"))):
        return {"ok": True}

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        employee_id=1, username="ali", full_name="Ali", roles=["EMPLOYEE"]
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/protected")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_require_roles_allows_matching_role():
    app = FastAPI()

    @app.get("/protected")
    async def protected(user=Depends(require_roles("HRBP"))):
        return {"ok": True}

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        employee_id=1, username="ali", full_name="Ali", roles=["EMPLOYEE", "HRBP"]
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/protected")

    assert response.status_code == 200