from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/fomobot_re"
    database_url_sync: str = "postgresql+psycopg2://user:password@localhost:5432/fomobot_re"

    @model_validator(mode="after")
    def _normalize_db_urls(self) -> "Settings":
        def to_asyncpg(url: str) -> str:
            if url.startswith("postgresql://") or url.startswith("postgres://"):
                return url.replace("://", "+asyncpg://", 1)
            return url

        def to_psycopg2(url: str) -> str:
            if url.startswith("postgresql://") or url.startswith("postgres://"):
                return url.replace("://", "+psycopg2://", 1)
            if url.startswith("postgresql+asyncpg://"):
                return url.replace("+asyncpg://", "+psycopg2://", 1)
            return url

        self.database_url = to_asyncpg(self.database_url)
        self.database_url_sync = to_psycopg2(self.database_url_sync)
        return self

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    # CORS
    allowed_origins: str = "http://localhost:5173,http://localhost:4173"

    # Sentry
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    # Scheduler — dev only
    enable_scheduler: bool = False

    # Health check
    health_stale_days: int = 40

    # MOLIT API key (공공데이터포털 서비스키)
    molit_api_key: str = ""

    # 수집 설정
    re_min_transaction_count: int = 5
    re_api_call_delay_sec: float = 0.3
    re_backfill_max_gu_per_run: int = 30
    re_backfill_start_year_month: str = "200601"


settings = Settings()
