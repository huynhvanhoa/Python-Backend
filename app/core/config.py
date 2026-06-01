from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    app_name: str = "Python Backend"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./app.db"

    # Admin API protection: set ALLOW_INSECURE_ADMIN=false in production.
    admin_api_key: str | None = None
    allow_insecure_admin: bool = True

    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str
    cloudinary_folder: str = "admin_uploads"
    cloudinary_upload_retries: int = 3
    cloudinary_retry_base_seconds: float = 1.0

    # Upload request throttling per client IP.
    upload_rate_limit_max_requests: int = 10
    upload_rate_limit_window_seconds: int = 60

    # Background queue fallback when cloud upload is throttled.
    upload_queue_retry_attempts: int = 8
    upload_queue_retry_delay_seconds: float = 10.0
    upload_queue_retry_backoff_multiplier: float = 2.0
    upload_queue_retry_max_delay_seconds: float = 120.0
    upload_queue_retry_jitter_seconds: float = 1.0

    # Observability
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Prefer environment variables over project .env in production deployments.
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )


settings = Settings()
