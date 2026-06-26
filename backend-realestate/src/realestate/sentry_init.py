import logging

logger = logging.getLogger(__name__)


def init_sentry(release: str | None = None) -> None:
    from realestate.config import settings

    if not settings.sentry_dsn:
        return

    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        environment=settings.app_env,
        release=release,
        send_default_pii=True,
        enable_tracing=True,
        enable_logs=True,
    )
    logger.info("Sentry 초기화 완료 (env=%s)", settings.app_env)
