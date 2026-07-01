"""
Sentry SDK 초기화 — 웹 앱과 배치 스크립트 양쪽에서 공용으로 사용.

SENTRY_DSN 환경변수가 없으면 아무 것도 하지 않으므로 로컬 개발에서는 설정 불필요.
"""

import logging

logger = logging.getLogger(__name__)


def init_sentry(release: str | None = None) -> None:
    """DSN이 설정된 경우에만 Sentry를 초기화한다."""
    from fomobot.config import settings

    if not settings.sentry_dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        environment=settings.app_env,
        release=release,
        send_default_pii=True,
        enable_tracing=True,
        enable_logs=True,
        integrations=[
            # breadcrumb는 INFO 이상, 이슈 생성은 ERROR 이상만
            # yfinance WARNING("possibly delisted" 등)은 이슈로 올라오지 않음
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
    )
    logger.info("Sentry 초기화 완료 (env=%s)", settings.app_env)
