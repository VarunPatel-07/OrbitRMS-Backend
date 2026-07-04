from arq.connections import RedisSettings

from config.EnvConfig import EnvConfig

"""
We First Connect with the RedisSetting then we use the same host and the connection that we have used for the redis.
"""


def get_arq_connection_setting():
    return RedisSettings(
        host=EnvConfig.CACHED_DATABASE_HOST,
        port=int(EnvConfig.CACHED_DATABASE_PORT),
        password=EnvConfig.CACHED_DATABASE_PASSWORD if EnvConfig.BACKEND_APP_ENVIRONMENT == "PRODUCTION" else None,
        ssl=True if EnvConfig.BACKEND_APP_ENVIRONMENT == "PRODUCTION" else False,
        conn_timeout=5,
        conn_retries=5,
        conn_retry_delay=1,
        retry_on_timeout=True,
        max_connections=20,
    )
