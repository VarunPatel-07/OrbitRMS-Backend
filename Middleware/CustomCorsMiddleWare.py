from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from Config.EnvConfig import EnvConfig

BACKEND_APP_ENVIRONMENT = EnvConfig.BACKEND_APP_ENVIRONMENT

ALLOWED_APP_ORIGINS = {
    "https://app.orbitrms.com",
    "https://admin.orbitrms.com",
}


class CustomCorsModule(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):

        if request.method == "OPTIONS":
            response = Response(status_code=200)
        else:
            response = await call_next(request)

        origin = request.headers.get("origin")

        if request.url.path.startswith("/public/v1/inquiries"):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"

        if BACKEND_APP_ENVIRONMENT == "PRODUCTION":
            if origin in ALLOWED_APP_ORIGINS:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "*"
                response.headers["Access-Control-Allow-Credentials"] = "true"
        else:
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Allow-Credentials"] = "false"

        return response
