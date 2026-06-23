from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/fomobot"
    database_url_sync: str = "postgresql+psycopg2://user:password@localhost:5432/fomobot"

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    # Noise Filter - KOSPI
    kospi_min_market_cap: int = 100_000_000_000        # 1000억원
    kospi_min_avg_volume_30d: int = 1_000_000_000       # 10억원/일
    kospi_min_price: int = 1_000                        # 1,000원

    # Noise Filter - NASDAQ
    nasdaq_min_market_cap_usd: int = 500_000_000        # $5억
    nasdaq_min_avg_volume_30d_usd: int = 5_000_000      # $500만/일
    nasdaq_min_price_usd: float = 5.0                   # $5

    # Batch settings
    batch_size_nasdaq: int = 100
    nasdaq_batch_delay_sec: float = 2.0
    nasdaq_max_consec_failures: int = 5
    nasdaq_circuit_breaker_wait_sec: int = 1800         # 30분


settings = Settings()
