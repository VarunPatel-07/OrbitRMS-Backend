from dotenv import load_dotenv
from valkey import Valkey

from Config.EnvConfig import EnvConfig

load_dotenv(override=True)

BACKEND_APP_ENVIRONMENT = EnvConfig.BACKEND_APP_ENVIRONMENT


CACHED_DATABASE_HOST = EnvConfig.CACHED_DATABASE_HOST

CACHED_DATABASE_PORT = EnvConfig.CACHED_DATABASE_PORT

CACHED_DATABASE_PASSWORD = EnvConfig.CACHED_DATABASE_PASSWORD


if BACKEND_APP_ENVIRONMENT == "PRODUCTION":
    cache_database = Valkey(
        host=CACHED_DATABASE_HOST,
        port=CACHED_DATABASE_PORT,
        password=CACHED_DATABASE_PASSWORD,
        ssl=True,
        ssl_cert_reqs=None,  # Aiven uses self-signed certs
        decode_responses=True,
    )
else:
    cache_database = Valkey(
        host=CACHED_DATABASE_HOST, port=CACHED_DATABASE_PORT, decode_responses=True
    )
