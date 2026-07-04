from cloudflare import CloudflareError
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from config.EnvConfig import EnvConfig
from constants.constant import SUCCESS
from database.Database import db_dependencies
from middleware.RateLimiting import limiter
from middleware.UserAuthenticator import UserAuthenticatorMiddleware
from models.pydantic.HelperPydanticModel import (
    CreateCloudflareTurnStileWithManualModePydanticModel,
    VerifyTurnstileSetUpPydanticModal,
)
from routes.apiManager.clientInquiry.service import (
    create_cloudflare_turnstile_service_with_manual,
    fetch_client_inquiry_service,
    fetch_inquiry_form_service,
    handel_enable_client_inquiry_service,
    re_generate_api_credentials_service,
    verify_cloudflare_turnstile_setup_service,
)
from utils.responseMessages import ERROR_MESSAGE

ApiManager = APIRouter(prefix="/app/v1/api-manager", tags=["api-manager"])


API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING


@ApiManager.put("/client-inquiry/enable-api", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def enable_api_service(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        return await handel_enable_client_inquiry_service(db=db, org_id=user.organization_id)
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.API_MANAGER.UNABLE_TO_ENABLE_CLIENT_INQUIRY_API_RIGHT_NOW,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )


@ApiManager.get(path="/client-inquiry/status/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_client_inquiry_status(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        return await fetch_client_inquiry_service(db=db, org_id=user.organization_id)
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.API_MANAGER.UNABLE_TO_ENABLE_CLIENT_INQUIRY_API_RIGHT_NOW,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )


@ApiManager.get(path="/client-inquiry/re-generate", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def re_generate_api_credentials(
    request: Request,
    db: db_dependencies,
    id: str = Query(..., alias="id"),
    field_name: str = Query(..., alias="field_name"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        return await re_generate_api_credentials_service(db=db, field_name=field_name, inquiry_id=id)

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.API_MANAGER.UNABLE_TO_ENABLE_CLIENT_INQUIRY_API_RIGHT_NOW,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )


@ApiManager.get(path="/client-inquiry/forms/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_inquiry_forms(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
):

    try:
        return await fetch_inquiry_form_service(db=db, org_id=user.organization_id)

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.API_MANAGER.UNABLE_TO_ENABLE_CLIENT_INQUIRY_API_RIGHT_NOW,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )


@ApiManager.post("/client-inquiry/turnstile/create", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def crete_turnstile(
    request: Request,
    db: db_dependencies,
    data: CreateCloudflareTurnStileWithManualModePydanticModel,
    inquiry_form_id: str = Query(..., alias="id"),
    # turnstile_setup_mode: str = Query(..., alias="setup_mode"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        return await create_cloudflare_turnstile_service_with_manual(db=db, data=data, inquiry_form_id=inquiry_form_id)

    except CloudflareError as cloudflare_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Unable to Create Cloudflare Turnstile widget right now.",
                "success": SUCCESS.FALSE,
                "error": str(cloudflare_error),
            },
        )
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.API_MANAGER.UNABLE_TO_ENABLE_CLIENT_INQUIRY_API_RIGHT_NOW,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )


@ApiManager.post("/client-inquiry/turnstile/verify", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def verify_turnstile_setup(
    request: Request,
    db: db_dependencies,
    data: VerifyTurnstileSetUpPydanticModal,
    inquiry_form_id: str = Query(..., alias="id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        return await verify_cloudflare_turnstile_setup_service(
            request=request, db=db, data=data, inquiry_form_id=inquiry_form_id
        )

    except CloudflareError as cloudflare_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Unable to Create Cloudflare Turnstile widget right now.",
                "success": SUCCESS.FALSE,
                "error": str(cloudflare_error),
            },
        )
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.API_MANAGER.UNABLE_TO_ENABLE_CLIENT_INQUIRY_API_RIGHT_NOW,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )
