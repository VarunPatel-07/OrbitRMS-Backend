from dotenv import load_dotenv
from redis.asyncio import Redis

from Config.EnvConfig import EnvConfig

load_dotenv(override=True)

BACKEND_APP_ENVIRONMENT = EnvConfig.BACKEND_APP_ENVIRONMENT


CACHED_DATABASE_HOST = EnvConfig.CACHED_DATABASE_HOST

CACHED_DATABASE_PORT = EnvConfig.CACHED_DATABASE_PORT

CACHED_DATABASE_PASSWORD = EnvConfig.CACHED_DATABASE_PASSWORD


if BACKEND_APP_ENVIRONMENT in ["PRODUCTION", "BETA-STAGING", "STAGING"]:
    cache_database = Redis(
        host=CACHED_DATABASE_HOST,
        port=CACHED_DATABASE_PORT,
        password=CACHED_DATABASE_PASSWORD,
        ssl=True,
        decode_responses=True,
    )
else:
    cache_database = Redis(
        host=CACHED_DATABASE_HOST, port=CACHED_DATABASE_PORT, decode_responses=True
    )
