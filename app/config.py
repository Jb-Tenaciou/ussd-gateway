from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "dev-only-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    SESSION_TIMEOUT_SECONDS: int = 120
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCK_MINUTES: int = 5


settings = Settings()

if not settings.DATABASE_URL.startswith("sqlite") and (
    settings.SECRET_KEY.startswith("dev-only") or len(settings.SECRET_KEY) < 32
):
    raise RuntimeError("SECRET_KEY trop faible : générez-en une avec secrets.token_hex(32)")
