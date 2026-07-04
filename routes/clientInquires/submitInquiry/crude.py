import json

from fastapi import BackgroundTasks, status
from sqlalchemy import and_
from sqlalchemy.orm import joinedload, selectinload

from config.EnvConfig import EnvConfig
from constants.constant import SUCCESS
from database.Database import db_dependencies
from mailer.HtmlEmailBody import NewClientInquiryAccruedMail
from mailer.emailService.email_models import EmailSchema
from mailer.emailService.email_queue_service import email_sender_function
from models.pydantic.HelperPydanticModel import CommonCrudeFunctionReturnType
from models.sql import Models
from utils.helper.helper import is_valid_type, validate_field
from utils.responseMessages import ERROR_MESSAGE, SUCCESS_MESSAGE


async def verify_inquiry_credentials(
    db: db_dependencies, api_key: str, api_secret: str
) -> CommonCrudeFunctionReturnType:

    client_inquiry = db.query(Models.ClientInquires).filter(Models.ClientInquires.api_key == api_key).first()

    if not client_inquiry:
        return {
            "message": ERROR_MESSAGE.SUBMIT_INQUIRY.CLIENT_INQUIRE_NOT_FOUND,
            "status_code": status.HTTP_400_BAD_REQUEST,
            "success": SUCCESS.FALSE,
            "data": None,
        }

    if not client_inquiry.api_secrete == api_secret:
        return {
            "message": ERROR_MESSAGE.SUBMIT_INQUIRY.INVALID_API_SECRET,
            "status_code": status.HTTP_400_BAD_REQUEST,
            "success": SUCCESS.FALSE,
            "data": None,
        }

    if not client_inquiry.status:
        return {
            "message": ERROR_MESSAGE.SUBMIT_INQUIRY.API_IS_DISABLED,
            "status_code": status.HTTP_400_BAD_REQUEST,
            "success": SUCCESS.FALSE,
            "data": None,
        }

    return {
        "message": SUCCESS_MESSAGE.EXECUTION_SUCCESS_MESSAGE,
        "status_code": status.HTTP_200_OK,
        "success": SUCCESS.TRUE,
        "data": client_inquiry,
    }


async def get_inquiry_submission_context(
    db: db_dependencies, api_key: str, api_secret: str, form_id: str
) -> CommonCrudeFunctionReturnType:
    client_inquiry = (
        db.query(Models.ClientInquires)
        .filter(Models.ClientInquires.api_key == api_key)
        .options(
            joinedload(Models.ClientInquires.organization).joinedload(Models.Organization.general_info),
            joinedload(Models.ClientInquires.organization)
            .selectinload(Models.Organization.config_modules)
            .selectinload(Models.ConfigModule.inquiry_form_schema)
            .selectinload(Models.InquiryFormSchema.inquiry_form_fields),
        )
        .first()
    )

    if not client_inquiry:
        return {
            "message": ERROR_MESSAGE.SUBMIT_INQUIRY.CLIENT_INQUIRE_NOT_FOUND,
            "status_code": status.HTTP_400_BAD_REQUEST,
            "success": SUCCESS.FALSE,
            "data": None,
        }

    if client_inquiry.api_secrete != api_secret:
        return {
            "message": ERROR_MESSAGE.SUBMIT_INQUIRY.INVALID_API_SECRET,
            "status_code": status.HTTP_400_BAD_REQUEST,
            "success": SUCCESS.FALSE,
            "data": None,
        }

    if not client_inquiry.status:
        return {
            "message": ERROR_MESSAGE.SUBMIT_INQUIRY.API_IS_DISABLED,
            "status_code": status.HTTP_400_BAD_REQUEST,
            "success": SUCCESS.FALSE,
            "data": None,
        }

    organization = client_inquiry.organization

    if not organization:
        return {
            "message": ERROR_MESSAGE.ORGANIZATION_NOT_FOUND,
            "status_code": status.HTTP_404_NOT_FOUND,
            "success": SUCCESS.FALSE,
            "data": None,
        }

    if not organization.status:
        return {
            "message": ERROR_MESSAGE.SIGN_IN_ORG_INACTIVE,
            "status_code": status.HTTP_403_FORBIDDEN,
            "success": SUCCESS.FALSE,
            "data": None,
        }

    config_modules = organization.config_modules or []

    if not config_modules:
        return {
            "message": ERROR_MESSAGE.CONFIG_MODULE_NOT_FOUND,
            "status_code": status.HTTP_404_NOT_FOUND,
            "success": SUCCESS.FALSE,
            "data": None,
        }

    form_schema = None

    for config_module in config_modules:
        for inquiry_form_schema in config_module.inquiry_form_schema or []:
            if inquiry_form_schema.form_id == form_id:
                form_schema = inquiry_form_schema
                break

        if form_schema:
            break

    if not form_schema:
        return {
            "message": ERROR_MESSAGE.SUBMIT_INQUIRY.FORM_NOT_FOUND,
            "status_code": status.HTTP_404_NOT_FOUND,
            "success": SUCCESS.FALSE,
            "data": None,
        }

    return {
        "message": SUCCESS_MESSAGE.EXECUTION_SUCCESS_MESSAGE,
        "status_code": status.HTTP_200_OK,
        "success": SUCCESS.TRUE,
        "data": {
            "client_inquiry": client_inquiry,
            "organization": organization,
            "form_schema": form_schema,
        },
    }


async def get_organizations_data(db: db_dependencies, org_id: str) -> CommonCrudeFunctionReturnType:
    organization = (
        db.query(Models.Organization)
        .filter(Models.Organization.id == org_id)
        .options(joinedload(Models.Organization.general_info))
        .first()
    )

    if not organization:
        return {
            "message": ERROR_MESSAGE.ORGANIZATION_NOT_FOUND,
            "status_code": status.HTTP_404_NOT_FOUND,
            "success": SUCCESS.FALSE,
            "data": None,
        }

    if not organization.status:
        return {
            "message": ERROR_MESSAGE.SIGN_IN_ORG_INACTIVE,
            "status_code": status.HTTP_403_FORBIDDEN,
            "success": SUCCESS.FALSE,
            "data": None,
        }

    return {
        "message": SUCCESS_MESSAGE.EXECUTION_SUCCESS_MESSAGE,
        "status_code": status.HTTP_200_OK,
        "success": SUCCESS.TRUE,
        "data": organization,
    }


async def get_config_module_data(db: db_dependencies, org_id: str):
    config_module = db.query(Models.ConfigModule).filter(Models.ConfigModule.organization_id == org_id).first()
    return config_module


async def get_form_data(db: db_dependencies, form_id: str, config_module_id: str):
    form_schema = db.query(Models.InquiryFormSchema).filter(
        and_(
            Models.InquiryFormSchema.config_module_id == config_module_id,
            Models.InquiryFormSchema.form_id == form_id,
        )
    ).first()
    return form_schema


async def verify_form_schema_service(query_payload, form_fields) -> CommonCrudeFunctionReturnType:

    valid_fields = [field.field_name for field in form_fields]

    missing_fields = [key for key in valid_fields if key not in query_payload]

    if missing_fields:
        return {
            "message": ERROR_MESSAGE.SUBMIT_INQUIRY.MISSING_FIELDS_IN_PAYLOAD,
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "success": SUCCESS.FALSE,
            "data": {
                "fields_missing": missing_fields,
            },
        }

    extra_query_fields = [key for key in query_payload.keys() if key not in valid_fields]

    if extra_query_fields:
        return {
            "message": ERROR_MESSAGE.SUBMIT_INQUIRY.UNEXPECTED_FIELDS_IN_PAYLOAD,
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "success": SUCCESS.FALSE,
            "data": {
                "extra_form_field": extra_query_fields,
            },
        }

    form_entity_fields = [
        {
            "field_name": field.field_name,
            "type": field.type,
            "is_required_field": field.is_required_field,
        }
        for field in form_fields
        if field.is_required_field
    ]

    null_fields = [field for field in form_entity_fields if not validate_field(query_payload.get(field["field_name"]))]

    if null_fields:
        return {
            "message": ERROR_MESSAGE.SUBMIT_INQUIRY.REQUIRED_FIELD_CANT_BE_NULL,
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "success": SUCCESS.FALSE,
            "data": {
                "fields": [field["field_name"] for field in form_entity_fields],
            },
        }

    invalid_field_type_arr = []

    for field in form_entity_fields:
        if field["is_required_field"]:
            field_name = field["field_name"]
            field_type = field["type"]

            value = query_payload.get(field_name)

            if not is_valid_type(value, field_type):
                invalid_field_type_arr.append(f"Expected type '{field_type}' for the '{field_name}'")

    for invalid_type in invalid_field_type_arr:
        return {
            "message": invalid_type,
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "success": SUCCESS.FALSE,
            "data": None,
        }

    return {
        "message": SUCCESS_MESSAGE.EXECUTION_SUCCESS_MESSAGE,
        "status_code": status.HTTP_200_OK,
        "success": SUCCESS.TRUE,
        "data": form_entity_fields,
    }


async def save_inquiry_send_mail(
    db: db_dependencies,
    client_inquire_id: str,
    background_task: BackgroundTasks,
    organization_name: str,
    portal_slug: str,
    organization_profile_picture: str,
    form_schema,
    inquiry_data,
    query_payload,
):

    client_inquiry_data = Models.ClientInquiresData(
        form_id=form_schema.form_id,
        form_name=form_schema.form_name,
        data=inquiry_data,
        client_inquire_id=client_inquire_id,
    )

    db.add(client_inquiry_data)
    db.commit()
    db.refresh(client_inquiry_data)

    if form_schema.email_notification and form_schema.authorized_recipient_emails:

        email_data = {
            "recipients_email": json.loads(form_schema.authorized_recipient_emails),
            "subject": f"You’ve Got a New Client Inquiry on {organization_name}",
            "body": NewClientInquiryAccruedMail(
                f"{EnvConfig.FRONTEND_URL.strip()}/{portal_slug}/client-inquiry",
                organization_name,
                organization_logo=organization_profile_picture,
                client_details=query_payload,
            ),
        }

        email_instance = EmailSchema(**email_data)

        background_task.add_task(email_sender_function, email_instance)

    return {
        "message": SUCCESS_MESSAGE.CONTACT_FORM_SUBMITTED_SUCCESSFULLY,
        "success": SUCCESS.TRUE,
    }
