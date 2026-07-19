import json
from urllib.parse import urlparse

from fastapi import HTTPException, Request, status
from starlette.datastructures import UploadFile as StarletteUploadFile

from constants.constant import SUCCESS
from utils.responseMessages import ERROR_MESSAGE


async def parse_inquiry_payload(request: Request):
    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.SUBMIT_INQUIRY.INVALID_JSON,
                    "success": SUCCESS.FALSE,
                },
            )

        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": ERROR_MESSAGE.SUBMIT_INQUIRY.OBJECT_JSON_PAYLOAD,
                    "success": SUCCESS.FALSE,
                },
            )

        return payload

    if "multipart/form-data" in content_type:
        form = await request.form()
        payload = {}

        for key, value in form.multi_items():
            if isinstance(value, StarletteUploadFile):
                # If same file field comes multiple times, store it as list
                if key in payload:
                    if isinstance(payload[key], list):
                        payload[key].append(value)
                    else:
                        payload[key] = [payload[key], value]
                else:
                    payload[key] = value

            else:
                # Convert empty strings to None if you want cleaner validation
                if value == "":
                    parsed_value = None
                else:
                    try:
                        parsed_value = json.loads(value)
                    except Exception:
                        parsed_value = value

                # If same normal field comes multiple times, store it as list
                if key in payload:
                    if isinstance(payload[key], list):
                        payload[key].append(parsed_value)
                    else:
                        payload[key] = [payload[key], parsed_value]
                else:
                    payload[key] = parsed_value

        return payload

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail={
            "message": ERROR_MESSAGE.SUBMIT_INQUIRY.UNSUPPORTED_CONTENT_TYPE,
            "success": SUCCESS.FALSE,
        },
    )


def extract_hostname(value: str | None) -> str | None:

    if not value:
        return None

    parsed = urlparse(value)

    # Origin/Referer usually has scheme, but fallback just in case
    if parsed.hostname:
        return parsed.hostname.lower()

    return value.replace("https://", "").replace("http://", "").split("/")[0].lower()


def normalize_allowed_domains(value) -> list[str]:
    if not value:
        return []

    if isinstance(value, list):
        return [str(domain) for domain in value if domain]

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return []

        try:
            parsed_value = json.loads(value)
        except Exception:
            return [value]

        if isinstance(parsed_value, list):
            return [str(domain) for domain in parsed_value if domain]

        if parsed_value:
            return [str(parsed_value)]

    return []


def is_domain_allowed(hostname: str | None, allowed_domains: list[str]) -> bool:
    if not hostname:
        return False

    hostname = hostname.lower()

    normalized_allowed_domains = [
        domain.lower().replace("https://", "").replace("http://", "").strip("/") for domain in allowed_domains
    ]

    return hostname in normalized_allowed_domains


def validate_request_origin(request: Request, allowed_domains: list[str]) -> None:
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")

    origin_host = extract_hostname(origin)
    referer_host = extract_hostname(referer)

    

    is_allowed = is_domain_allowed(origin_host, allowed_domains) or is_domain_allowed(referer_host, allowed_domains)

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Request origin is not allowed for this form.",
                "success": False,
            },
        )
