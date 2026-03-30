import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from config.EnvConfig import EnvConfig


def initSentryMonitoring():

    if EnvConfig.BACKEND_APP_ENVIRONMENT == "PRODUCTION":
        sentry_sdk.init(
            dsn=EnvConfig.SENTRY_MONITORING_KEY,
            integrations=[FastApiIntegration()],
            environment=EnvConfig.BACKEND_APP_ENVIRONMENT,
            traces_sample_rate=1.0,
            send_default_pii=False,
        )
