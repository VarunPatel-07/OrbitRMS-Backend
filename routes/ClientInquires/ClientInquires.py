import json
import math
import os
from typing import Optional
from urllib.parse import unquote

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_
from sqlalchemy.orm import joinedload

from Database.Database import db_dependencies
from Email.HtmlEmailBody import NewClientInquiryAccruedMail
from Helper.emailSender import EmailSchema, email_sender_function
from Helper.helper import (
    filter_fields,
    is_valid_type,
    model_to_filtered_dict,
    validate_field,
)
from Middleware.UserAuthenticator import UserAuthenticatorMiddleware
from Middleware.verifyToken import verify_token
from RateLimiting import limiter
from SqlModels import Models

from .ClientInquiresQueryFilter import apply_client_inquiry_query_filter

load_dotenv(override=True)
API_RATE_LIMITING = os.getenv("API_RATE_LIMITING")

FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip()

clientInquires = APIRouter(prefix="/app/v1/client-inquires", tags=["clientInquires"])


#
# ? Fetch All The Client Inquiry Data That Have Been Submitted
#
@clientInquires.get(path="/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Fetch_Client_Inquires(
    request: Request,
    db: db_dependencies,
    page: int = Query(..., alias="page"),
    limit: int = Query(..., alias="limit"),
    filter: Optional[str] = Query(None),
    form_id: str = Query(..., alias="form_id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

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
            and_(
                Models.ClientInquiresData.client_inquire_id == client_inquires.id,
                Models.ClientInquiresData.form_id == form_id,
            )
        )
        total_data = 0

        page = page if page else 1
        limit = limit if limit else 10

        start = (page - 1) * limit
        end = start + limit

        if filter_data:
            query_data = apply_client_inquiry_query_filter(query_data, filter_data)
            total_data = query_data.count()
            query_data = query_data.offset(start).limit(end)

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
                    "form_id": _data.form_id,
                    "form_name": _data.form_name,
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


@clientInquires.delete("/delete-inquire")
@limiter.limit(API_RATE_LIMITING)
async def DeleteClientInquire(
    request: Request,
    db: db_dependencies,
    id: str = Query(..., alias="id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        client_inquiry = (
            db.query(Models.ClientInquiresData).filter(Models.ClientInquiresData.id == id).first()
        )
        if not client_inquiry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Client Inquiry Not Found", "success": False},
            )
        db.delete(client_inquiry)
        db.commit()

        return {"message": "Inquiry Deleted Successfully", "success": True}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable Delete Inquiry Right Now",
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
    form_id: str = Query(..., alias="form_id"),
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
        form_schema = (
            db.query(Models.InquiryFormSchema)
            .filter(
                and_(
                    Models.InquiryFormSchema.config_module_id == config_module.id,
                    Models.InquiryFormSchema.form_id == form_id,
                )
            )
            .first()
        )

        if not form_schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Invalid Form Type",
                    "extra_form_field": extra_form_field,
                    "success": False,
                },
            )

        form_fields = (
            db.query(Models.InquiryFormFields)
            .filter(Models.InquiryFormFields.inquiry_form_schema_id == form_schema.id)
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
            form_id=form_schema.form_id,
            form_name=form_schema.form_name,
            data=payload,
            client_inquire_id=client_inquires.id,
        )

        db.add(client_inquiry_data)
        db.commit()
        db.refresh(client_inquiry_data)

        if client_inquires.email_notification and client_inquires.authorized_recipient_emails:

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
