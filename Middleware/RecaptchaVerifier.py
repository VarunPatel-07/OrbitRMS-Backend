import aiohttp
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from Config.EnvConfig import EnvConfig


async def verify_recaptcha(token: str) -> str:
    url = "https://www.google.com/recaptcha/api/siteverify"

    data = {
        "secret": EnvConfig.GOOGLE_RECAPTCHA_SECRET_KEY,
        "response": token,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url=url, data=data) as response:
            return await response.json()


class RecaptchaMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # 🔥 PROTECTED ROUTES (only these need recaptcha)
        not_protected_paths = [
            "/app/v1/client-inquires/submit",
        ]

        if request.url.path in not_protected_paths:
            return await call_next(request)
        try:
            # Only verify for protected paths

            token = request.headers.get("X-Recaptcha-Token")

            if not token:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Missing reCAPTCHA token header"},
                )

            verification = await verify_recaptcha(token)

            if not verification.get("success"):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "reCAPTCHA failed"},
                )

            if verification.get("score", 0) < 0.5:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Bot detected (low score)"},
                )

        except Exception as e:

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error in RecaptchaMiddleware"},
            )

        # Continue to next middleware/route
        return await call_next(request)
