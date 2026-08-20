from fastapi import FastAPI
from app.api.routes.auth import router as auth_router
from app.api.routes.teams import router as teams_router
from app.core.exceptions import APIException
from app.core.exception_handlers import api_exception_handler
from app.api.routes.employees import router as employee_router
from app.api.routes.me import router as me_router

tags_metadata = [
    {
        "name" : "Auth",
        "description" : "Authentication, token lifecycle, and current authenticated-user endpoints."
    },
    {
        "name": "Teams",
        "description": "Team structure, team membership, managers, and HRBP assignments."
    },
    {
        "name": "Employees",
        "description": "Employee creation, profile management, visibility, status, and employee-scoped resources."
    }
]


app = FastAPI(
    title = "Career Journey API",
    version = "0.1.0",
    servers=[
        {"url": "/api/v1"}
    ],
    openapi_tags=tags_metadata
)

app.add_exception_handler(APIException, api_exception_handler)

app.include_router(
    auth_router,
    tags=["Auth"]
    )
app.include_router(
    teams_router,
    tags=["Teams"]
    )

app.include_router(employee_router, tags=["Employees"])
app.include_router(me_router, tags=["Employees"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}