from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str
    
    auth_issuer: str
    auth_audience: str = "authenticated"
    
    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "UTF-8",
        extra = "ignore"
    )
        

settings = Settings()