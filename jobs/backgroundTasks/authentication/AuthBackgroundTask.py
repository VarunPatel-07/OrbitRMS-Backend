import json

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from config.EnvConfig import EnvConfig
from database.Database import SessionLocal
from mailer.HtmlEmailBody import (
    VerifyEmailHtmlBody,
)
from mailer.emailService.email_models import EmailSchema
from mailer.emailService.email_queue_service import email_sender_function
from models.pydantic.authentication.AuthenticationModels import (
    RegisterOrganizationInfo,
)
from models.pydantic.HelperPydanticModel import (
    VerifyEmailPydanticBody,
)
from models.sql import Models
from utils.helper.createModelInstance import cerate_model_instance
from utils.helper.encryption_helper import urlsafe_data_encoding_service

FRONTEND_URL = EnvConfig.FRONTEND_URL


def HandelUserSignUpInBackGround(
    organization_id: str,
    organization_info: RegisterOrganizationInfo,
):
    db: Session = SessionLocal()

    find_organization = db.query(Models.Organization).filter(Models.Organization.id == organization_id).first()

    if find_organization:

        domain = organization_info.primary_email.split("@")[1]

        organization = cerate_model_instance(
            model=Models.OrganizationGeneralInfo,
            data=organization_info,
            fields=["-country_info", "-indexed_email_domain"],
        )
        organization.indexed_email_domain = domain
        user_info = Models.User(password="", organization_id=organization_id)
        db.add(user_info)
        db.flush()

        user_employee_info = Models.EmployeeInfo(
            status="Confirmed",
            organization_name=organization_info.organization_name,
            employee_code="",
            department="",
            designation="",
            employee_email=organization_info.primary_email,
            user_id=user_info.id,
        )

        db.add(user_employee_info)

        organization.organization_id = organization_id

        organization.country_info = json.dumps(
            organization_info.country_info.dict()
            if hasattr(organization_info.country_info, "dict")
            else organization_info.country_info
        )

        db.add(organization)
        db.commit()

        encrypted_org_id = urlsafe_data_encoding_service(organization_id)

        email_data = {
            "recipients_email": organization_info.primary_email,
            "subject": "Verify Your Email Address to Activate Your OrbitRMS Account",
            "body": VerifyEmailHtmlBody(
                VerifyEmailPydanticBody(
                    confirm_my_email=f"{FRONTEND_URL}/verification/verify-email?organization-id={encrypted_org_id}",
                    organization_name=organization_info.organization_name,
                )
            ),
        }

        email_instance = EmailSchema(**email_data)

        email_sender_function(email_instance)
