from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field, field_validator, model_validator
from pathlib import Path
from urllib.parse import urlsplit


class Settings(BaseSettings):
    # Resolve the backend-local environment file independent of the shell's CWD.
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
        populate_by_name=True,
    )
    app_env: str = "development"
    secret_key: str = "development-only-change-me"
    database_url: str = Field(
    default="sqlite:///./astroai.db",
        validation_alias=AliasChoices(
            "DATABASE_URL",
            "POSTGRES_PRISMA_URL",
            "database_url",
        ),
    )
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:5173"
    trusted_proxy_ips: str = ""
    ai_chat_rate_limit_per_minute: int = Field(default=30, gt=0)
    password_reset_rate_limit_per_hour: int = Field(default=5, gt=0)
    password_reset_ip_rate_limit_per_hour: int = Field(default=20, gt=0)
    password_reset_smtp_host: str | None = None
    password_reset_smtp_port: int = Field(default=587, ge=1, le=65535)
    password_reset_smtp_username: str | None = None
    password_reset_smtp_password: str | None = None
    password_reset_smtp_sender: str | None = None
    password_reset_smtp_starttls: bool = True
    password_reset_frontend_url: str = "http://localhost:5173"
    password_reset_dev_token_file: str | None = None
    geoapify_api_key: str | None = None
    geocoding_request_timeout_seconds: float = Field(default=5.0, gt=0, le=20)
    geocoding_rate_limit_per_minute: int = Field(default=20, gt=0)
    swisseph_ephe_path: str | None = None
    swisseph_library_path: str | None = None
    astrology_calculations_enabled: bool = False
    swisseph_license_confirmed: bool = False
    astrology_local_agpl_development_enabled: bool = False

    @field_validator("app_env")
    @classmethod
    def supported_environment(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized not in {"development", "test", "staging", "production", "prod"}:
            raise ValueError("APP_ENV must be development, test, staging or production")
        return normalized

    @field_validator("password_reset_frontend_url")
    @classmethod
    def valid_password_reset_frontend_url(cls, value: str) -> str:
        parsed = urlsplit(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("PASSWORD_RESET_FRONTEND_URL must be an HTTP(S) origin or base path without credentials, query, or fragment")
        return value.strip().rstrip("/")

    @model_validator(mode="after")
    def production_configuration_is_safe(self):
        if self.astrology_local_agpl_development_enabled and self.app_env != "development":
            raise ValueError("ASTROLOGY_LOCAL_AGPL_DEVELOPMENT_ENABLED is permitted only in development")
        if self.password_reset_dev_token_file and self.app_env != "development":
            raise ValueError("PASSWORD_RESET_DEV_TOKEN_FILE is allowed only in development")
        smtp_values = (self.password_reset_smtp_host, self.password_reset_smtp_sender)
        if any(smtp_values) and not all(smtp_values):
            raise ValueError("Password reset SMTP requires both host and sender configuration")
        if bool(self.password_reset_smtp_username) != bool(self.password_reset_smtp_password):
            raise ValueError("Password reset SMTP username and password must be configured together")
        if self.app_env in {"production", "prod", "staging"} and self.password_reset_email_configured and not self.password_reset_smtp_starttls:
            raise ValueError("Password reset SMTP must use STARTTLS in staging and production")
        if self.app_env not in {"production", "prod", "staging"}:
            return self
        reset_url = urlsplit(self.password_reset_frontend_url)
        if reset_url.scheme != "https":
            raise ValueError("Staging and production password reset frontend URLs must use HTTPS")
        if self.secret_key == "development-only-change-me" or len(self.secret_key) < 32:
            raise ValueError("Production requires a unique SECRET_KEY of at least 32 characters")
        if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://", "postgres://")):
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
    def password_reset_email_configured(self) -> bool:
        return bool(self.password_reset_smtp_host and self.password_reset_smtp_sender)

    @property
    def password_reset_local_file_configured(self) -> bool:
        return self.app_env == "development" and bool(self.password_reset_dev_token_file)

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def trusted_proxy_ip_list(self) -> list[str]:
        return [item.strip() for item in self.trusted_proxy_ips.split(",") if item.strip()]

    @property
    def astrology_calculations_authorized(self) -> bool:
        local_agpl = self.app_env == "development" and self.astrology_local_agpl_development_enabled
        return local_agpl or (self.astrology_calculations_enabled and self.swisseph_license_confirmed)


settings = Settings()
