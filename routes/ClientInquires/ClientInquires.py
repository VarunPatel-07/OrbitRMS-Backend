import json
import math
import os
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from Email.HtmlEmailBody import NewClientInquiryAccruedMail
from Helper.emailSender import EmailSchema, email_sender_function

from Database.Database import db_dependencies
from Helper.helper import (
    filter_fields,
    generate_api_secrets_api_key,
    is_valid_type,
    model_to_filtered_dict,
    validate_field,
)
from Middleware.verifyToken import verify_token
from RateLimiting import limiter
from SqlModels import Models
from PydanticModels.Organizations.organizations import AuthorizedRecipientEmail

from .ClientInquiresQueryFilter import apply_client_inquiry_query_filter

API_RATE_LIMITING = os.getenv("API_RATE_LIMITING")

FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip()

clientInquires = APIRouter(prefix="/app/v1/client-inquires", tags=["clientInquires"])


#
# ? This Is An Api Which Is Used To Enable Or Disable The Api That Mens it Shows That The Current Status Of The Api
#
@clientInquires.put("/enable-api", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Enable_Api(request: Request, db: db_dependencies, token: str = Depends(verify_token)):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        session_id = token["session_id"]

        user = (
            db.query(Models.User)
            .options(joinedload(Models.User.sessions), joinedload(Models.User.organization))
            .filter(Models.User.id == user_id)
            .first()
        )

        if not user or not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Account is deactivated. Access denied."
                        if user.account_status
                        else "User Not Found"
                    ),
                    "success": False,
                },
            )

        if not user.organization.status:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        if not any(session.id == session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
                headers={"WWW-Authenticate": "Bearer"},
            )

        client_inquires = (
            db.query(Models.ClientInquires)
            .filter(Models.ClientInquires.organization_id == user.organization_id)
            .first()
        )

        if not client_inquires:
            api_key, api_secret = generate_api_secrets_api_key()
            create_client_inquires = Models.ClientInquires(
                api_key=api_key, api_secrete=api_secret, organization_id=user.organization_id
            )

            db.add(create_client_inquires)
            db.commit()
            db.refresh(create_client_inquires)

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
@clientInquires.get(path="/status/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Fetch_Status_OF_Api(
    request: Request, db: db_dependencies, token: str = Depends(verify_token)
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        session_id = token["session_id"]

        user = (
            db.query(Models.User)
            .options(joinedload(Models.User.sessions), joinedload(Models.User.organization))
            .filter(Models.User.id == user_id)
            .first()
        )

        if not user or not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Account is deactivated. Access denied."
                        if user.account_status
                        else "User Not Found"
                    ),
                    "success": False,
                },
            )
        if not user.organization.status:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        if not any(session.id == session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
                headers={"WWW-Authenticate": "Bearer"},
            )

        client_inquires = (
            db.query(Models.ClientInquires)
            .filter(Models.ClientInquires.organization_id == user.organization_id)
            .first()
        )

        return {
            "message": "Data Fetched Successfully",
            "success": True,
            "data": (
                {
                    **model_to_filtered_dict(
                        client_inquires, fields=["-authorized_recipient_emails"]
                    ),
                    "authorized_recipient_emails": json.loads(
                        client_inquires.authorized_recipient_emails
                    ),
                }
                if client_inquires
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


#
# ? Fetch All The Client Inquiry Data That Have Been Submitted
#
@clientInquires.get(path="/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Fetch_Client_Inquires(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    page: int = Query(..., alias="page"),
    limit: int = Query(..., alias="limit"),
    filter: Optional[str] = Query(None),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        session_id = token["session_id"]

        user = (
            db.query(Models.User)
            .options(joinedload(Models.User.sessions), joinedload(Models.User.organization))
            .filter(Models.User.id == user_id)
            .first()
        )

        if not user or not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Account is deactivated. Access denied."
                        if user.account_status
                        else "User Not Found"
                    ),
                    "success": False,
                },
            )

        if not user.organization.status:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        if not any(session.id == session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
                headers={"WWW-Authenticate": "Bearer"},
            )

        client_inquires = (
            db.query(Models.ClientInquires)
            .filter(Models.ClientInquires.organization_id == user.organization_id)
            .first()
        )

        filter_data = ""
        if filter:
            decoded = unquote(filter)
            filter_data = json.loads(decoded)

        if not client_inquires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Client Inquiry Not Found", "success": False},
            )

        query_data = db.query(Models.ClientInquiresData).filter(
            Models.ClientInquiresData.client_inquire_id == client_inquires.id
        )
        total_data = 0

        page = page if page else 1
        limit = limit if limit else 10

        start = (page - 1) * limit
        end = start + limit

        if filter_data:
            query_data = apply_client_inquiry_query_filter(query_data, filter_data)
            total_data = len(query_data)
            query_data = query_data[start:end]

        else:
            total_data = query_data.count()

            query_data = query_data.offset(start).limit(end)

        return {
            "message": "Client Inquiry Fetched Successfully",
            "success": True,
            "data": [
                {
                    **filter_fields(_data.data, ["-client_inquire_id", "-id"]),
                    "client_inquire_id": _data.client_inquire_id,
                    "id": _data.id,
                }
                for _data in query_data
            ],
            "metadata": {
                "total_data": total_data,
                "total_pages": math.ceil(total_data / limit),
                "current_page": page,
                "record_per_page": limit,
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


@clientInquires.put(path="/re-generate", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def ReGenerateKeys(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    id: str = Query(..., alias="id"),
    field_name: str = Query(..., alias="field_name"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        session_id = token["session_id"]

        user = (
            db.query(Models.User)
            .options(joinedload(Models.User.sessions), joinedload(Models.User.organization))
            .filter(Models.User.id == user_id)
            .first()
        )

        if not user or not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Account is deactivated. Access denied."
                        if user.account_status
                        else "User Not Found"
                    ),
                    "success": False,
                },
            )
        if not user.organization.status:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        if not any(session.id == session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
                headers={"WWW-Authenticate": "Bearer"},
            )

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


@clientInquires.put("/enable-mail-notification")
@limiter.limit(API_RATE_LIMITING)
async def EnableMailNotification(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    id: str = Query(..., alias="id"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        session_id = token["session_id"]

        user = (
            db.query(Models.User)
            .options(joinedload(Models.User.sessions), joinedload(Models.User.organization))
            .filter(Models.User.id == user_id)
            .first()
        )

        if not user or not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Account is deactivated. Access denied."
                        if user.account_status
                        else "User Not Found"
                    ),
                    "success": False,
                },
            )
        if not user.organization.status:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        if not any(session.id == session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
            )

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
            "email_notification": client_inquires.email_notification,
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


@clientInquires.put("/add-authorized-recipient")
@limiter.limit(API_RATE_LIMITING)
async def EnableMailNotification(
    request: Request,
    db: db_dependencies,
    data: AuthorizedRecipientEmail,
    token: str = Depends(verify_token),
    id: str = Query(..., alias="id"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        session_id = token["session_id"]

        user = (
            db.query(Models.User)
            .options(joinedload(Models.User.sessions), joinedload(Models.User.organization))
            .filter(Models.User.id == user_id)
            .first()
        )

        if not user or not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Account is deactivated. Access denied."
                        if user.account_status
                        else "User Not Found"
                    ),
                    "success": False,
                },
            )
        if not user.organization.status:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        if not any(session.id == session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
            )

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
            "authorized_recipient_email": json.loads(client_inquires.authorized_recipient_emails),
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


@clientInquires.post(path="/submit", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def submit_inquiry(
    request: Request,
    db: db_dependencies,
    background_task: BackgroundTasks,
    payload: dict,
    api_key: str = Query(..., alias="api_key"),
    api_secret: str = Query(..., alias="api_secret"),
):
    try:
        client_inquires = (
            db.query(Models.ClientInquires).filter(Models.ClientInquires.api_key == api_key).first()
        )
        if not client_inquires:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Client Inquire Not Found",
                    "success": False,
                },
            )

        if not client_inquires.api_secrete == api_secret:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Invalid Api Secrete",
                    "success": False,
                },
            )

        if not client_inquires.status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Api Is Disabled",
                    "success": False,
                },
            )

        organization = (
            db.query(Models.Organization)
            .filter(Models.Organization.id == client_inquires.organization_id)
            .options(joinedload(Models.Organization.general_info))
            .first()
        )

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "organization not found", "success": False},
            )
        if not organization.status:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        config_module = (
            db.query(Models.ConfigModule)
            .filter(Models.ConfigModule.organization_id == client_inquires.organization_id)
            .first()
        )

        if not config_module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Config Module Not Found",
                    "success": False,
                },
            )
        form_fields = (
            db.query(Models.ClientFormSchema)
            .filter(Models.ClientFormSchema.config_module_id == config_module.id)
            .all()
        )

        # now we will allow only that field that are in the form field
        valid_field = [field.field_name for field in form_fields]

        extra_form_field = [key for key in payload.keys() if key not in valid_field]

        if extra_form_field:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Unexpected fields in payload",
                    "extra_form_field": extra_form_field,
                    "success": False,
                },
            )

        required_fields = [
            {
                "field_name": field.field_name,
                "type": field.type,
                "is_required_field": field.is_required_field,
            }
            for field in form_fields
            if field.is_required_field
        ]

        missing_fields = [field for field in required_fields if field["field_name"] not in payload]

        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Missing required fields",
                    "success": False,
                },
            )

        null_required_field = [
            field
            for field in required_fields
            if not validate_field(payload.get(field["field_name"]))
        ]

        if null_required_field:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Required Field Can't Be Null",
                    "success": False,
                    "fields": [field["field_name"] for field in null_required_field],
                },
            )

        invalid_type_fields = []

        for field in required_fields:
            if field["is_required_field"]:
                field_name = field["field_name"]
                field_type = field["type"]

                value = payload.get(field_name)

                if not is_valid_type(value, field_type):
                    invalid_type_fields.append(
                        f"Expected type '{field_type}' for the '{field_name}'"
                    )

        for invalid_type in invalid_type_fields:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": invalid_type,
                    "missing_fields": missing_fields,
                    "success": False,
                },
            )

        client_inquiry_data = Models.ClientInquiresData(
            data=payload, client_inquire_id=client_inquires.id
        )

        db.add(client_inquiry_data)
        db.commit()
        db.refresh(client_inquiry_data)

        if client_inquires.email_notification:

            email_data = {
                "recever_email": json.loads(client_inquires.authorized_recipient_emails),
                "subject": f"You’ve Got a New Client Inquiry on {organization.general_info.organization_name}",
                "body": NewClientInquiryAccruedMail(
                    f"{FRONTEND_URL}/{organization.general_info.portal_slug}/client-inquiry",
                    organization.general_info.organization_name,
                ),
            }

            email_instance = EmailSchema(**email_data)

            email_sender_function(email_instance, background_task)

        return {
            "message": "Contact Form Submitted Successfully",
            "success": True,
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Add Submit Inquiry Right Now",
                "success": False,
                "error": str(e),
            },
        )
