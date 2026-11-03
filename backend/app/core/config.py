from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
from urllib.parse import urlsplit


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")
    app_env: str = "development"
    secret_key: str = "development-only-change-me"
    database_url: str = "sqlite:///./astroai.db"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:5173"
    ai_free_daily_limit: int = 20
    swisseph_ephe_path: str | None = None
    swisseph_library_path: str | None = None
    astrology_calculations_enabled: bool = False
    swisseph_license_confirmed: bool = False

    @field_validator("app_env")
    @classmethod
    def supported_environment(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized not in {"development", "test", "staging", "production", "prod"}:
            raise ValueError("APP_ENV must be development, test, staging or production")
        return normalized

    @model_validator(mode="after")
    def production_configuration_is_safe(self):
        if self.app_env not in {"production", "prod", "staging"}:
            return self
        if self.secret_key == "development-only-change-me" or len(self.secret_key) < 32:
            raise ValueError("Production requires a unique SECRET_KEY of at least 32 characters")
        if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("Production requires PostgreSQL; SQLite is only supported for local testing")
        origins = self.cors_origin_list
        parsed_origins = [urlsplit(origin) for origin in origins]
        if not origins or "*" in origins or any(
            item.scheme != "https" or not item.hostname or item.username or item.password
            or item.path not in {"", "/"} or item.query or item.fragment
            for item in parsed_origins
        ):
            raise ValueError("Production CORS_ORIGINS must contain explicit HTTPS origins")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
