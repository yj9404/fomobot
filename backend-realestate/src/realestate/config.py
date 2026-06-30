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

    # Health check — 마지막 월별 스냅샷이 이 개월 수 이상 뒤처지면 unhealthy
    # 한국 부동산 실거래가는 통상 1~2개월 후행 공개되므로 3개월을 기본값으로 사용
    health_stale_months: int = 3

    # MOLIT API key (공공데이터포털 서비스키)
    molit_api_key: str = ""

    # 수집 설정
    re_api_call_delay_sec: float = 0.3
    re_backfill_max_gu_per_run: int = 30
    re_backfill_start_year_month: str = "200601"

    # 단지 랭킹 설정
    # 윈도우 N: 시작·종료 앵커 기준으로 탐색할 월 수
    #   시작 앵커: [start-N, start+N] (대칭, 3m 구간은 [start-N, start] 과거 방향만)
    #   종료 앵커: [end-N, end]       (미래 방향 차단)
    re_window_months: int = 3
    # 최소 거래건수 M: 시작·종료 앵커 양쪽 모두 M건 이상이어야 랭킹 포함
    re_min_tx_per_window: int = 3


settings = Settings()
