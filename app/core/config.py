from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str
    database_url: str

    auth_issuer: str
    auth_audience: str

    supabase_url: str
    supabase_publishable_key: str
    supabase_service_role_key: str | None = None

    db_pool_size: int = 20
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()