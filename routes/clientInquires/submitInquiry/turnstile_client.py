import httpx

from config.EnvConfig import EnvConfig

_turnstile_http_client: httpx.AsyncClient | None = None


async def init_turnstile_http_client() -> None:
    global _turnstile_http_client

    if _turnstile_http_client is None:
        _turnstile_http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(5.0, connect=2.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )


async def close_turnstile_http_client() -> None:
    global _turnstile_http_client

    if _turnstile_http_client is not None:
        await _turnstile_http_client.aclose()
        _turnstile_http_client = None


async def verify_turnstile_token(payload: dict) -> dict:
    if _turnstile_http_client is None:
        await init_turnstile_http_client()

    response = await _turnstile_http_client.post(
        url=EnvConfig.CLOUDFLARE_TURNSTILE_VERIFY_URL,
        data=payload,
    )

    return response.json()
