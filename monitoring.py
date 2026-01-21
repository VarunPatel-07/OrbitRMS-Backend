import sentry_sdk
from config.EnvConfig import EnvConfig
from constants.constant import (
    PRODUCTION_ENVIRONMENT,
    SENTRY_TRACE_SAMPLE_RATE,
    SENTRY_SEND_DEFAULT_PII,
)
from sentry_sdk.integrations.fastapi import FastApiIntegration


def initSentryMonitoring():

    if EnvConfig.BACKEND_APP_ENVIRONMENT == PRODUCTION_ENVIRONMENT:
        sentry_sdk.init(
            dsn=EnvConfig.SENTRY_MONITORING_KEY,
            integrations=[FastApiIntegration()],
            environment=EnvConfig.BACKEND_APP_ENVIRONMENT,
            traces_sample_rate=SENTRY_TRACE_SAMPLE_RATE,
            send_default_pii=SENTRY_SEND_DEFAULT_PII,
        )
