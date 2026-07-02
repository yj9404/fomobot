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

    _YFINANCE_NOISE = ("possibly delisted", "no price data found")

    def _before_send(event, hint):
        # yfinance가 logger.error()로 찍는 상폐/데이터 없음 메시지는 이슈가 아님
        msg = event.get("message") or event.get("logentry", {}).get("message", "")
        if any(phrase in msg for phrase in _YFINANCE_NOISE):
            return None
        return event

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        environment=settings.app_env,
        release=release,
        send_default_pii=True,
        enable_tracing=True,
        enable_logs=True,
        before_send=_before_send,
        integrations=[
            # breadcrumb는 INFO 이상, 이슈 생성은 ERROR 이상만
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
    )
    logger.info("Sentry 초기화 완료 (env=%s)", settings.app_env)
