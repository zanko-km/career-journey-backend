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
from pathlib import Path
from alembic import command
from alembic.config import Config
import sys
import asyncio
from datetime import date
from app.models.user import User
from app.models.employee import Employee
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from app.core.database import get_db
from app.main import app



ALEMBIC_INI_PATH = Path(__file__).resolve().parent.parent / "alembic.ini"
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


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    alembic_cfg = Config(str(ALEMBIC_INI_PATH))
    alembic_cfg.set_main_option("sqlalchemy.url", test_settings.database_url)
    command.upgrade(alembic_cfg, "head")


@pytest_asyncio.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(test_settings.database_url)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.connect() as connection:
        transaction = await connection.begin()

        session = session_factory(bind=connection)

        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()

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

@pytest_asyncio.fixture
async def provisioned_test_employee(db_session):
    settings = TestAuthSettings()
    supabase = create_client(settings.supabase_url, settings.supabase_publishable_key)

    response = supabase.auth.sign_in_with_password({
        "email": settings.test_user_email,
        "password": settings.test_user_password,
    })

    employee = Employee(username="test@gmail.com", full_name="Test Employee", join_date=date.today())
    db_session.add(employee)
    await db_session.flush()

    user = User(auth_provider_id=str(response.user.id), employee_id=employee.id)
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()

    return employee