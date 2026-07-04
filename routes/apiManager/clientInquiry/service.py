import json

import httpx
from fastapi import HTTPException, Query, Request, status

from config.EnvConfig import EnvConfig
from constants.constant import SUCCESS
from database.Database import db_dependencies
from models.pydantic.HelperPydanticModel import (
    CreateCloudflareTurnStileWithManualModePydanticModel,
    VerifyTurnstileSetUpPydanticModal,
)
from routes.apiManager.clientInquiry.crude import fetch_inquiry_form, get_client_inquiry, get_inquiry_forms_data
from utils.helper.encryption_helper import decrypt_data_service, encrypt_data_service
from utils.helper.helper import generate_api_secrets_api_key, model_to_filtered_dict
from utils.responseMessages import ERROR_MESSAGE, SUCCESS_MESSAGE


# This is the service in which we are handling the enabling the client inquiry
async def handel_enable_client_inquiry_service(db: db_dependencies, org_id: str):

    client_inquiry = await get_client_inquiry(db=db, org_id=org_id)

    if not client_inquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": ERROR_MESSAGE.SUBMIT_INQUIRY.CLIENT_INQUIRE_NOT_FOUND,
                "success": SUCCESS.FALSE,
            },
        )

    client_inquiry.status = False if client_inquiry.status else True

    if not client_inquiry.api_key or not client_inquiry.api_secrete:
        api_key, api_secret = generate_api_secrets_api_key()

        client_inquiry.api_key = api_key if not client_inquiry.api_key else client_inquiry.api_key

        client_inquiry.api_secrete = api_secret if not client_inquiry.api_secrete else client_inquiry.api_secrete

    db.commit()
    db.refresh(client_inquiry)

    return {
        "message": (
            SUCCESS_MESSAGE.API_MANAGER.API_ENABLED_SUCCESSFULLY
            if client_inquiry.status
            else SUCCESS_MESSAGE.API_MANAGER.API_DISABLED_SUCCESSFULLY
        ),
        "success": SUCCESS.TRUE,
    }


# Here we are fetching the client inquiry details
async def fetch_client_inquiry_service(db: db_dependencies, org_id: str):
    client_inquiry = await get_client_inquiry(db=db, org_id=org_id)

    if not client_inquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": ERROR_MESSAGE.SUBMIT_INQUIRY.CLIENT_INQUIRE_NOT_FOUND,
                "success": SUCCESS.FALSE,
            },
        )

    return {
        "message": SUCCESS_MESSAGE.INQUIRY_SCHEMA_FETCHED_SUCCESSFULLY,
        "success": SUCCESS.TRUE,
        "data": (
            {
                **model_to_filtered_dict(
                    client_inquiry,
                ),
            }
            if client_inquiry
            else None
        ),
    }


# This is an function for the re Generating the api credentials
async def re_generate_api_credentials_service(
    db: db_dependencies,
    inquiry_id: str = Query(..., alias="id"),
    field_name: str = Query(..., alias="field_name"),
):
    if field_name not in ["api_key", "api_secrete"]:
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail={"message": ERROR_MESSAGE.API_MANAGER.INVALID_QUERY_ARGUMENT, "success": SUCCESS.FALSE},
        )

    client_inquiry = await get_client_inquiry(db=db, inquiry_id=inquiry_id)

    if not client_inquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": ERROR_MESSAGE.SUBMIT_INQUIRY.CLIENT_INQUIRE_NOT_FOUND,
                "success": SUCCESS.FALSE,
            },
        )

    api_key, api_secret = generate_api_secrets_api_key()

    if field_name == "api_key":
        client_inquiry.api_key = api_key

    elif field_name == "api_secret":
        client_inquiry.api_secrete = api_secret

    db.commit()
    db.refresh(client_inquiry)

    return {"message": f"{field_name} Updated Successfully", "success": SUCCESS.TRUE}


async def fetch_inquiry_form_service(db: db_dependencies, org_id: str):

    inquiry_forms = await get_inquiry_forms_data(db=db, org_id=org_id)

    return {
        "message": SUCCESS_MESSAGE.API_MANAGER.INQUIRY_FORM_FETCHED_SUCCESSFULLY,
        "success": SUCCESS.TRUE,
        "data": (
            [
                model_to_filtered_dict(
                    data,
                    fields=[
                        "id",
                        "form_id",
                        "form_name",
                        "status",
                        "email_notification",
                        "turnstile_enabled",
                        "turnstile_site_key",
                        "turnstile_mode",
                        "allowed_domains",
                        "turnstile_verification_status",
                        "turnstile_secret_key",
                    ],
                )
                for data in inquiry_forms
            ]
            if inquiry_forms
            else []
        ),
    }


async def create_cloudflare_turnstile_service_with_manual(
    db: db_dependencies,
    data: CreateCloudflareTurnStileWithManualModePydanticModel,
    inquiry_form_id: str = Query(..., alias="id"),
):
    inquiry_form = await fetch_inquiry_form(db=db, inquiry_form_id=inquiry_form_id)

    if not inquiry_form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": ERROR_MESSAGE.API_MANAGER.INQUIRE_FORM_NOT_FOUND,
                "success": SUCCESS.FALSE,
            },
        )

    if not data.turnstile_site_key or not data.turnstile_secret_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.API_MANAGER.TURNSTILE_SITE_KEY_SECRET_KEY_REQUIRED,
                "success": SUCCESS.FALSE,
            },
        )

    if not data.turnstile_site_key.startswith("0x"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.API_MANAGER.TURNSTILE_SITE_KEY_FORMATE,
                "success": SUCCESS.FALSE,
            },
        )

    inquiry_form.turnstile_enabled = True
    inquiry_form.turnstile_site_key = encrypt_data_service(data.turnstile_site_key)
    inquiry_form.turnstile_secret_key = encrypt_data_service(data.turnstile_secret_key)
    inquiry_form.turnstile_mode = data.turnstile_mode
    inquiry_form.allowed_domains = json.dumps(data.allowed_domains)

    db.commit()
    db.refresh(inquiry_form)

    return {
        "message": SUCCESS_MESSAGE.API_MANAGER.TURNSTILE_WIDGET_CREATED_SUCCESSFULLY,
        "success": SUCCESS.TRUE,
        "data": {"turnstile_site_key": inquiry_form.turnstile_site_key},
    }


async def verify_cloudflare_turnstile_setup_service(
    request: Request,
    db: db_dependencies,
    data: VerifyTurnstileSetUpPydanticModal,
    inquiry_form_id: str = Query(..., alias="id"),
):

    try:

        inquiry_form = await fetch_inquiry_form(db=db, inquiry_form_id=inquiry_form_id)

        if not inquiry_form:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": ERROR_MESSAGE.API_MANAGER.INQUIRE_FORM_NOT_FOUND,
                    "success": SUCCESS.FALSE,
                },
            )

        try:
            decrypted_secret_key = decrypt_data_service(inquiry_form.turnstile_secret_key)

            if isinstance(decrypted_secret_key, bytes):
                decrypted_secret_key = decrypted_secret_key.decode("utf-8")

            decrypted_secret_key = decrypted_secret_key.strip().strip('"').strip("'")

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"success": False, "message": "Unable to decrypt Turnstile secret key.", "error": e},
            )

        cloudflare_payload = {
            "secret": decrypted_secret_key,
            "response": data.turnstile_token,
            "remoteip": request.client.host if request.client else None,
        }

        async with httpx.AsyncClient(timeout=10) as client:
            cloudflare_response = await client.post(
                url=EnvConfig.CLOUDFLARE_TURNSTILE_VERIFY_URL, data=cloudflare_payload
            )

            cloudflare_result = cloudflare_response.json()

        if not cloudflare_result.get("success"):
            inquiry_form.turnstile_enabled = False
            inquiry_form.turnstile_verification_status = "failed"

            db.commit()
            db.refresh(inquiry_form)

            return {
                "success": False,
                "message": "Turnstile verification failed. Please make sure the required domain is added in Cloudflare allowed domains.",
                "error_codes": cloudflare_result,
            }
        inquiry_form.turnstile_enabled = True
        inquiry_form.turnstile_verification_status = "verified"

        db.commit()
        db.refresh(inquiry_form)

        return {"success": True, "message": "Turnstile setup verified successfully.", "data": None}

    except HTTPException:
        raise

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "Unable to verify Turnstile setup right now.",
                "error": str(error),
            },
        )
