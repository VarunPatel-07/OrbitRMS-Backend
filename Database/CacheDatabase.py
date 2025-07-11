import os

from dotenv import load_dotenv
from redis.asyncio import Redis

load_dotenv(override=True)

BACKEND_APP_ENVIRONMENT = os.getenv("BACKEND_APP_ENVIRONMENT")


CACHED_DATABASE_HOST = os.getenv("CACHED_DATABASE_HOST")

CACHED_DATABASE_PORT = os.getenv("CACHED_DATABASE_PORT")

CACHED_DATABASE_PASSWORD = os.getenv("CACHED_DATABASE_PASSWORD")


if BACKEND_APP_ENVIRONMENT == "PRODUCTION":
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
