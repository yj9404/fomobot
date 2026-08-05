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

    def _before_send(event, hint):
        # yfinance가 logger.error()로 찍는 개별 종목 조회 실패(상폐, 데이터 없음,
        # Yahoo 쪽 500/파싱 오류 등)는 배치가 다음 티커로 넘어가며 정상 처리하는
        # 노이즈이지 우리 코드의 이슈가 아님. 티커별로 메시지가 달라 필터링을
        # 문구 매칭이 아닌 logger 이름 기준으로 통째로 제외한다.
        if event.get("logger") == "yfinance":
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
