from fastapi import FastAPI
from app.api.routes.auth import router as auth_router
from app.api.routes.teams import router as teams_router
app = FastAPI(
    title = "Career Journey API",
    version = "0.1.0"
)
app.include_router(
    auth_router,
    prefix="/api/v1"
    )
app.include_router(
    teams_router,
    prefix="/api/v1"
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}