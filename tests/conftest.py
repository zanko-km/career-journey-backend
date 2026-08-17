import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from supabase import create_client
from app.main import app

class TestSettings(BaseSettings):
    database_url: str
    
    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        extra="ignore",
    )

class TestAuthSettings(BaseSettings):
    supabase_url: str
    supabase_publishable_key: str
    test_user_email: str
    test_user_password: str

    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
test_settings = TestSettings()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(test_settings.database_url)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()
    

@pytest.fixture
def supabase_access_token():
    settings = TestAuthSettings()

    supabase = create_client(
        settings.supabase_url,
        settings.supabase_publishable_key,
    )

    response = supabase.auth.sign_in_with_password(
        {
            "email": settings.test_user_email,
            "password": settings.test_user_password,
        }
    )

    if response.session is None:
        raise RuntimeError("Could not authenticate test user")

    return response.session.access_token