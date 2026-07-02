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
    # Railway PostgreSQL은 "postgresql://..." 형태로 주입하므로 드라이버 prefix를 자동 보정
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/fomobot"
    database_url_sync: str = "postgresql+psycopg2://user:password@localhost:5432/fomobot"

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

    # CORS — 콤마로 구분된 허용 오리진 목록
    # 예: "http://localhost:5173,https://fomobot.vercel.app"
    allowed_origins: str = "http://localhost:5173,http://localhost:4173"

    # Sentry — 값이 없으면 초기화 스킵
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    # Scheduler — true 이면 웹 프로세스에서 APScheduler 실행 (dev 전용)
    # prod 에서는 Railway Cron 이 fomobot.jobs.collect 를 직접 호출하므로 false
    enable_scheduler: bool = False

    # Noise Filter - KOSPI
    kospi_min_market_cap: int = 100_000_000_000        # 1000억원
    kospi_min_avg_volume_30d: int = 1_000_000_000       # 10억원/일
    kospi_min_price: int = 1_000                        # 1,000원

    # Noise Filter - NASDAQ
    nasdaq_min_market_cap_usd: int = 500_000_000        # $5억
    nasdaq_min_avg_volume_30d_usd: int = 5_000_000      # $500만/일
    nasdaq_min_price_usd: float = 5.0                   # $5

    # NASDAQ corporate action / sanity filters
    # True: market_cap=0(미수집)인 종목을 랭킹에서 제외 (보수적)
    # False(기본): 기존 동작 유지 - market_cap 미수집이면 시총 조건 생략
    nasdaq_exclude_unknown_market_cap: bool = False
    # 단일 거래일 변동률 상한 (pct_change 기준, 3.0 = 300%)
    # 이 값을 초과하는 날이 하나라도 있으면 데이터 오염(액면분할·병합)으로 간주해 제외
    nasdaq_max_daily_move_pct: float = 3.0
    # 연율화 변동성 상한 (%) — 이를 초과하면 이중 안전장치로 추가 제외
    nasdaq_max_volatility_pct: float = 1000.0

    # Batch settings
    batch_size_nasdaq: int = 100
    nasdaq_batch_delay_sec: float = 2.0
    nasdaq_max_consec_failures: int = 5
    nasdaq_circuit_breaker_wait_sec: int = 1800         # 30분

    # price_daily retention
    # 랭킹 계산이 1825d(5년) 기간을 사용하므로 최소 2000일치 데이터 보존 필요.
    # cleanup 잡이 이 값 이전 데이터를 DELETE한다.
    price_daily_retention_days: int = 2000


settings = Settings()
