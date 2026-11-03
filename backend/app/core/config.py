from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")
    app_env: str = "development"
    secret_key: str = "development-only-change-me"
    database_url: str = "sqlite:///./astroai.db"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:5173"
    # Dormant legacy provider adapter settings. Deterministic chat does not read these.
    ai_provider: str = "openai-compatible"
    ai_base_url: str | None = None
    ai_api_key: str | None = None
    ai_model: str | None = None
    ai_timeout_seconds: float = 30.0
    ai_max_tokens: int = 1200
    ai_free_daily_limit: int = 20
    swisseph_ephe_path: str | None = None
    swisseph_library_path: str | None = None
    astrology_calculations_enabled: bool = False
    swisseph_license_confirmed: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
