from pydantic_settings import BaseSettings, SettingsConfigDict
from supabase import create_client


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

print(response.session.access_token)