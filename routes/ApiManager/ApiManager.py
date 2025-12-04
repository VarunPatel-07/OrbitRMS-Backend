import json
import os

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy.orm import joinedload

from Config.EnvConfig import EnvConfig
from Database.Database import db_dependencies
from Helper.helper import generate_api_secrets_api_key, model_to_filtered_dict
from Middleware.UserAuthenticator import UserAuthenticatorMiddleware
from PydanticModels.Organizations.organizations import AuthorizedRecipientEmail
from RateLimiting import limiter
from SqlModels import Models

load_dotenv(override=True)

API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING

ApiManager = APIRouter(prefix="/app/v1/api-manager", tags=["api-manger"])


#
# ? This Is An Api Which Is Used To Enable Or Disable The Api That Mens it Shows That The Current Status Of The Api
#
@ApiManager.put("/client-inquiry/enable-api", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Enable_Api(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        client_inquires = (
            db.query(Models.ClientInquires)
            .filter(Models.ClientInquires.organization_id == user.organization_id)
            .first()
        )

        if not client_inquires:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Client Inquiry Not Found", "success": False},
            )

        else:

            client_inquires.status = False if client_inquires.status else True

            if not client_inquires.api_key or not client_inquires.api_secrete:

                api_key, api_secret = generate_api_secrets_api_key()

                client_inquires.api_key = (
                    api_key if not client_inquires.api_key else client_inquires.api_key
                )

                client_inquires.api_secrete = (
                    api_secret if not client_inquires.api_secrete else client_inquires.api_secrete
                )

        db.commit()
        db.refresh(client_inquires)

        return {
            "message": (
                "Api Enabled Successfully" if client_inquires.status else "Api Disable Successfully"
            ),
            "enable": client_inquires.status,
            "success": True,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Enable Api Right Now",
                "success": False,
                "error": str(e),
            },
        )


#
# ? Fetch All The Client Inquiry Data That Have Been Submitted
#
@ApiManager.get(path="/client-inquiry/status/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Fetch_Status_OF_Api(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        client_inquire = (
            db.query(Models.ClientInquires)
            .filter(Models.ClientInquires.organization_id == user.organization_id)
            .first()
        )
        config_module = (
            db.query(Models.ConfigModule)
            .filter(Models.ConfigModule.organization_id == user.organization_id)
            .first()
        )

        inquiry_form_schemas = (
            db.query(Models.InquiryFormSchema)
            .filter(Models.InquiryFormSchema.config_module_id == config_module.id)
            .all()
        )

        return {
            "message": "Data Fetched Successfully",
            "success": True,
            "data": (
                {
                    **model_to_filtered_dict(
                        client_inquire,
                    ),
                    "inquiry_form_schemas": [
                        model_to_filtered_dict(
                            data,
                            fields=[
                                "form_id",
                                "id",
                                "form_name",
                                "status",
                                "email_notification",
                                "authorized_recipient_emails",
                            ],
                        )
                        for data in inquiry_form_schemas
                    ],
                }
                if client_inquire
                else None
            ),
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Some Thing Went Wrong",
                "success": False,
                "error": str(e),
            },
        )


@ApiManager.put(path="/client-inquiry/re-generate", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def ReGenerateKeys(
    request: Request,
    db: db_dependencies,
    id: str = Query(..., alias="id"),
    field_name: str = Query(..., alias="field_name"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        if field_name not in ["api_key", "api_secrete"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={"message": "Invalid Field_Name", "success": False},
            )

        client_inquires = (
            db.query(Models.ClientInquires).filter(Models.ClientInquires.id == id).first()
        )

        if not client_inquires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Client Inquiry Not Found", "success": False},
            )
        api_key, api_secret = generate_api_secrets_api_key()
        if field_name == "api_key":
            client_inquires.api_key = api_key
        elif field_name == "api_secrete":
            client_inquires.api_secrete = api_secret
        db.commit()
        db.refresh(client_inquires)

        return {"message": f"{field_name} Updated Successfully", "success": True}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Enable Api Right Now",
                "success": False,
                "error": str(e),
            },
        )


@ApiManager.put("/client-inquiry/enable-mail-notification")
@limiter.limit(API_RATE_LIMITING)
async def EnableMailNotification(
    request: Request,
    db: db_dependencies,
    id: str = Query(..., alias="id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        client_inquires = (
            db.query(Models.ClientInquires).filter(Models.ClientInquires.id == id).first()
        )

        if not client_inquires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Client Inquiry Not Found", "success": False},
            )

        client_inquires.email_notification = not client_inquires.email_notification

        db.commit()
        db.refresh(client_inquires)

        return {
            "message": f"Updated Successfully",
            "success": True,
            "data": {
                "email_notification": client_inquires.email_notification,
            },
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Enable Api Right Now",
                "success": False,
                "error": str(e),
            },
        )


@ApiManager.put("/client-inquiry/add-authorized-recipient")
@limiter.limit(API_RATE_LIMITING)
async def EnableMailNotification(
    request: Request,
    db: db_dependencies,
    data: AuthorizedRecipientEmail,
    id: str = Query(..., alias="id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        client_inquires = (
            db.query(Models.ClientInquires).filter(Models.ClientInquires.id == id).first()
        )

        if not client_inquires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Client Inquiry Not Found", "success": False},
            )

        client_inquires.authorized_recipient_emails = json.dumps(data.authorized_recipient)

        db.commit()
        db.refresh(client_inquires)

        return {
            "message": f"Updated Successfully",
            "success": True,
            "data": {
                "authorized_recipient_email": json.loads(
                    client_inquires.authorized_recipient_emails
                ),
            },
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Enable Api Right Now",
                "success": False,
                "error": str(e),
            },
        )
