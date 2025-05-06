import os

from dotenv import load_dotenv
from redis.asyncio import Redis

load_dotenv(override=True)


cached_redis_host = os.getenv("CACHED_DATABASE_HOST")

cached_redis_port = os.getenv("CACHED_DATABASE_PORT")


cache_database = Redis(host=cached_redis_host, port=cached_redis_port, decode_responses=True)
