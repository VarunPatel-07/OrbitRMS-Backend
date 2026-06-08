import asyncio
import json

import cloudinary
from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import and_
from sqlalchemy.orm import joinedload

from config.EnvConfig import EnvConfig
from constants.constant import SUCCESS
from database.Database import db_dependencies
from mailer.HtmlEmailBody import NewClientInquiryAccruedMail
from middleware.RateLimiting import limiter
from models.sql import Models
from utils.helper.emailSender import EmailSchema, email_sender_function
from utils.helper.helper import (
    is_valid_type,
    validate_field,
)
from utils.responseMessages import ERROR_MESSAGE, SUCCESS_MESSAGE

load_dotenv(override=True)
API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING

FRONTEND_URL = EnvConfig.FRONTEND_URL.strip()

CLOUDINARY_API_SECRET = EnvConfig.CLOUDINARY_API_SECRET
CLOUDINARY_API_KEY = EnvConfig.CLOUDINARY_API_KEY
CLOUDINARY_CLOUD_NAME = EnvConfig.CLOUDINARY_CLOUD_NAME

publicInquiryRouter = APIRouter(prefix="/public/v1/inquiries", tags=["clientInquires"])

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
)


async def upload_single_file(file: UploadFile):
    file_bytes = await file.read()

    result = await run_in_threadpool(
        cloudinary.uploader.upload,
        file_bytes,
        resource_type="image",
    )

    return result["secure_url"]


import json
from fastapi import Request, HTTPException, status
from starlette.datastructures import UploadFile as StarletteUploadFile


async def parse_inquiry_payload(request: Request):
    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Invalid JSON payload.",
                    "success": SUCCESS.FALSE,
                },
            )

        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "JSON payload must be an object.",
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
            "message": "Unsupported content type. Use application/json or multipart/form-data.",
            "success": SUCCESS.FALSE,
        },
    )


@publicInquiryRouter.post(path="/submit", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def submit_inquiry(
    request: Request,
    db: db_dependencies,
    background_task: BackgroundTasks,
    api_key: str = Query(..., alias="api_key"),
    api_secret: str = Query(..., alias="api_secret"),
    form_id: str = Query(..., alias="form_id"),
):
    try:
        payload = await parse_inquiry_payload(request)

        print("payload", payload)

        client_inquires = db.query(Models.ClientInquires).filter(Models.ClientInquires.api_key == api_key).first()
        if not client_inquires:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": ERROR_MESSAGE.CLIENT_INQUIRE_NOT_FOUND,
                    "success": SUCCESS.FALSE,
                },
            )

        if not client_inquires.api_secrete == api_secret:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": ERROR_MESSAGE.INVALID_API_SECRET,
                    "success": SUCCESS.FALSE,
                },
            )

        if not client_inquires.status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": ERROR_MESSAGE.API_IS_DISABLED,
                    "success": SUCCESS.FALSE,
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
                detail={"message": ERROR_MESSAGE.ORGANIZATION_NOT_FOUND, "success": SUCCESS.FALSE},
            )
        if not organization.status:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": ERROR_MESSAGE.SIGN_IN_ORG_INACTIVE,
                    "success": SUCCESS.FALSE,
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
                    "message": ERROR_MESSAGE.CONFIG_MODULE_NOT_FOUND,
                    "success": SUCCESS.FALSE,
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
                    "message": ERROR_MESSAGE.FORM_ID_NOT_FOUND,
                    "success": SUCCESS.FALSE,
                },
            )

        form_fields = (
            db.query(Models.InquiryFormFields)
            .filter(Models.InquiryFormFields.inquiry_form_schema_id == form_schema.id)
            .all()
        )

        # now we will allow only that field that are in the form field
        valid_field = [field.field_name for field in form_fields]

        missing_fields = [key for key in valid_field if key not in payload]

        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": ERROR_MESSAGE.MISSING_FIELDS_IN_PAYLOAD,
                    "fields_missing": missing_fields,
                    "success": SUCCESS.FALSE,
                },
            )

        extra_form_field = [key for key in payload.keys() if key not in valid_field]

        if extra_form_field:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": ERROR_MESSAGE.UNEXPECTED_FIELDS_IN_PAYLOAD,
                    "extra_form_field": extra_form_field,
                    "success": SUCCESS.FALSE,
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

        missing_required_fields = [
            field for field in required_fields if field["field_name"] not in payload
        ]

        if missing_required_fields:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": ERROR_MESSAGE.MISSING_REQUIRED_FIELDS,
                    "success": SUCCESS.FALSE,
                },
            )

        null_required_field = [
            field for field in required_fields if not validate_field(payload.get(field["field_name"]))
        ]

        if null_required_field:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": ERROR_MESSAGE.REQUIRED_FIELD_CANT_BE_NULL,
                    "success": SUCCESS.FALSE,
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
                    invalid_type_fields.append(f"Expected type '{field_type}' for the '{field_name}'")

        for invalid_type in invalid_type_fields:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": invalid_type,
                    "missing_fields": missing_fields,
                    "success": False,
                },
            )

        inquiry_data = {}
        for field in required_fields:
            field_name = field["field_name"]
            field_type = field["type"]

            value = payload.get(field_name)

            if field_type == "file":
                print("file", value)
                files_value = value if isinstance(value, list) else [value]
                uploaded_files = await asyncio.gather(
                    *(upload_single_file(file) for file in files_value)
                )
                inquiry_data[field_name] = uploaded_files
            else:
                inquiry_data[field_name] = value

        client_inquiry_data = Models.ClientInquiresData(
            form_id=form_schema.form_id,
            form_name=form_schema.form_name,
            data=inquiry_data,
            client_inquire_id=client_inquires.id,
        )

        db.add(client_inquiry_data)
        db.commit()
        db.refresh(client_inquiry_data)

        if form_schema.email_notification and form_schema.authorized_recipient_emails:

            email_data = {
                "recever_email": json.loads(form_schema.authorized_recipient_emails),
                "subject": f"You’ve Got a New Client Inquiry on {organization.general_info.organization_name}",
                "body": NewClientInquiryAccruedMail(
                    f"{FRONTEND_URL}/{organization.general_info.portal_slug}/client-inquiry",
                    organization.general_info.organization_name,
                    organization_logo=organization.general_info.organization_profile_picture,
                    client_details=payload,
                ),
            }

            email_instance = EmailSchema(**email_data)

            email_sender_function(email_instance, background_task)

        return {
            "message": SUCCESS_MESSAGE.CONTACT_FORM_SUBMITTED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.UNABLE_TO_SUBMIT_INQUIRY,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )
