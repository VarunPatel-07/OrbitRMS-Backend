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
from sqlalchemy.orm import aliased, joinedload

from config.EnvConfig import EnvConfig
from constants.constant import SUCCESS
from database.Database import db_dependencies
from mailer.HtmlEmailBody import CreatePasswordHtmlBody, VerifyEmailHtmlBody
from middleware.RateLimiting import limiter
from middleware.verifyToken import verify_token
from models.pydantic.Admin.AdminAuthenticationModel import ResendVerificationMail
from models.pydantic.HelperPydanticModel import (
    CreatePasswordPydanticBody,
    VerifyEmailPydanticBody,
)
from models.sql import Models
from utils.helper.emailSender import EmailSchema, email_sender_function
from utils.helper.helper import (
    filter_fields,
    generatePasswordResetToken,
    model_to_filtered_dict,
    urlsafe_data_encoding_function,
)
from utils.responseMessages import ERROR_MESSAGE, SUCCESS_MESSAGE

from .OrganizationQueryFilters import Apply_Organization_Query_Filter

FRONTEND_URL = EnvConfig.FRONTEND_URL.strip()
load_dotenv(override=True)

adminOrgRoute = APIRouter(prefix="/app/v1/admin/organization-manager", tags=["admin"])
API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING


@adminOrgRoute.get(path="/fetch-organizations", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Fetch_All__Organization(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    page: int = Query(..., alias="page"),
    limit: int = Query(..., alias="limit"),
    filter: Optional[str] = Query(None),
):
    try:
        if token is None or not isinstance(token, dict):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.UNAUTHORIZED, "success": SUCCESS.FALSE},
            )

        admin_id = token["admin_id"]
        session_id = token["session_id"]
        admin_signature = token["admin_signature"]

        admin = (
            db.query(Models.Admin)
            .options(joinedload(Models.Admin.admin_sessions))
            .filter(Models.Admin.id == admin_id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.INVALID_SESSION, "success": SUCCESS.FALSE},
            )

        filter_data: str = ""

        if filter:
            decoded = unquote(filter)
            filter_data = json.loads(decoded)

        org_query_data = db.query(Models.Organization)

        if org_query_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": ERROR_MESSAGE.NO_ORGANIZATIONS_FOUND, "success": SUCCESS.FALSE},
            )

        org_query_data = org_query_data.outerjoin(Models.Organization.general_info)
        org_query_data = org_query_data.outerjoin(Models.Organization.address)

        if filter_data:
            org_query_data = Apply_Organization_Query_Filter(org_query_data, filter_data)

        total_data = org_query_data.count()
        page = page if page else 1
        limit = limit if limit else 10
        start = (page - 1) * limit
        end = start + limit
        org_query_data = org_query_data.offset(start).limit(end)

        org_query_data = org_query_data.options(
            joinedload(Models.Organization.general_info),
            joinedload(Models.Organization.address),
            joinedload(Models.Organization.contact_info),
            joinedload(Models.Organization.about_info),
            joinedload(Models.Organization.organization_settings),
        )

        organizations = org_query_data.all()

        return {
            "message": SUCCESS_MESSAGE.ORGANIZATIONS_FETCHED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": [
                {
                    **model_to_filtered_dict(org),
                    **(
                        {
                            "primary_email": org.general_info.primary_email,
                            "primary_number": org.general_info.primary_number,
                            "organization_name": org.general_info.organization_name,
                            "organization_image": org.general_info.organization_profile_picture,
                        }
                        if org.general_info
                        else {}
                    ),
                    "email_domain_slug": (
                        org.organization_settings.email_domain_slug
                        if org.organization_settings
                        else None
                    ),
                    "is_meta_verified": (
                        org.general_info.is_meta_verified if org.general_info else None
                    ),
                    "email_verified": org.general_info.email_verified if org.general_info else None,
                    "employee_code_prefix": (
                        org.organization_settings.employee_code_prefix
                        if org.organization_settings
                        else None
                    ),
                    "intern_code_prefix": (
                        org.organization_settings.intern_code_prefix
                        if org.organization_settings
                        else None
                    ),
                    "country_info": (
                        (
                            json.loads(org.general_info.country_info)
                            if isinstance(org.general_info.country_info, str)
                            else org.general_info.country_info
                        )
                        if org.general_info
                        else None
                    ),
                    "portal_slug": org.general_info.portal_slug if org.general_info else None,
                    "organization_address": (
                        {
                            "country": org.address[0].country,
                            "country_code": org.address[0].country_code,
                        }
                        if org.address
                        else None
                    ),
                }
                for org in organizations
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
                "message": ERROR_MESSAGE.ADMIN_VERIFICATION_ERROR,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@adminOrgRoute.put(path="/organization-setting/status", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Organization_Setting(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    id: str = Query(..., alias="id"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.UNAUTHORIZED, "success": SUCCESS.FALSE},
            )

        admin_id = token["admin_id"]
        session_id = token["session_id"]
        admin_signature = token["admin_signature"]

        admin = (
            db.query(Models.Admin)
            .options(joinedload(Models.Admin.admin_sessions))
            .filter(Models.Admin.id == admin_id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.INVALID_SESSION, "success": SUCCESS.FALSE},
            )

        organization = db.query(Models.Organization).filter(Models.Organization.id == id).first()

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": ERROR_MESSAGE.ORGANIZATION_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        organization.status = True if not organization.status else False

        db.commit()
        db.refresh(organization)

        return {
            "message": "Organizations fetched successfully",
            "success": SUCCESS.TRUE,
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ADMIN_VERIFICATION_ERROR,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@adminOrgRoute.get(path="/client-organization/details")
@limiter.limit(API_RATE_LIMITING)
async def Fetch_Client_Organization_Details(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    id: str = Query(..., alias="id"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.UNAUTHORIZED, "success": SUCCESS.FALSE},
            )

        admin_id = token["admin_id"]
        session_id = token["session_id"]
        admin_signature = token["admin_signature"]

        admin = (
            db.query(Models.Admin)
            .options(joinedload(Models.Admin.admin_sessions))
            .filter(Models.Admin.id == admin_id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.INVALID_SESSION, "success": SUCCESS.FALSE},
            )

        organization = (
            db.query(Models.Organization)
            .options(
                joinedload(Models.Organization.general_info),
                joinedload(Models.Organization.address),
                joinedload(Models.Organization.contact_info),
                joinedload(Models.Organization.about_info),
                joinedload(Models.Organization.organization_settings),
            )
            .filter(Models.Organization.id == id)
            .first()
        )

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": ERROR_MESSAGE.ORGANIZATION_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        return {
            "message": SUCCESS_MESSAGE.INFO_FETCHED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": {
                **model_to_filtered_dict(organization),
                "general_info": (
                    {
                        "country_info": (
                            json.loads(organization.general_info.country_info)
                            if isinstance(organization.general_info.country_info, str)
                            else organization.general_info.country_info
                        ),
                        **filter_fields(
                            organization.general_info,
                            ["-id", "-organization_id", "-country_info"],
                        ),
                    }
                    if organization.general_info
                    else None
                ),
                "address": (
                    filter_fields(organization.address[0], ["-id", "-organization_id"])
                    if organization.address
                    else None
                ),
                "contact_info": [
                    filter_fields(contact_info, ["-id", "-organization_id"])
                    for contact_info in organization.contact_info
                ],
                "about_info": (
                    filter_fields(organization.about_info[0], ["-id", "-organization_id"])
                    if organization.about_info
                    else None
                ),
                "organization_settings": (
                    filter_fields(organization.organization_settings, ["-id", "-organization_id"])
                    if organization.organization_settings
                    else None
                ),
            },
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ADMIN_VERIFICATION_ERROR,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@adminOrgRoute.post(path="/reset/resend-email-verification")
@limiter.limit(API_RATE_LIMITING)
async def Resend_Email_Verification_Link(
    request: Request,
    db: db_dependencies,
    data: ResendVerificationMail,
    background_task: BackgroundTasks,
    token: str = Depends(verify_token),
    id: str = Query(..., alias="id"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.UNAUTHORIZED, "success": SUCCESS.FALSE},
            )

        admin_id = token["admin_id"]
        session_id = token["session_id"]
        admin_signature = token["admin_signature"]

        admin = (
            db.query(Models.Admin)
            .options(joinedload(Models.Admin.admin_sessions))
            .filter(Models.Admin.id == admin_id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.INVALID_SESSION, "success": SUCCESS.FALSE},
            )

        find_organization = (
            db.query(Models.OrganizationGeneralInfo)
            .filter(Models.OrganizationGeneralInfo.primary_email == data.email)
            .first()
        )

        domain = data.email.split("@")[1]

        check_for_the_email_domain = (
            db.query(Models.Organization)
            .join(Models.OrganizationGeneralInfo)
            .filter(
                Models.OrganizationGeneralInfo.indexed_email_domain == domain,
                Models.Organization.status.is_(True),
            )
            .first()
        )

        if check_for_the_email_domain:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": ERROR_MESSAGE.EMAIL_DOMAIN_ALREADY_IN_USE,
                    "success": SUCCESS.FALSE,
                },
            )

        if find_organization:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": ERROR_MESSAGE.ORGANIZATION_ALREADY_EXISTS,
                    "success": SUCCESS.FALSE,
                    "owner_email": find_organization.primary_email,
                },
            )

        organization = db.query(Models.Organization).filter(Models.Organization.id == id).first()

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": ERROR_MESSAGE.ORGANIZATION_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        organization_general_info = (
            db.query(Models.OrganizationGeneralInfo)
            .filter(Models.OrganizationGeneralInfo.organization_id == organization.id)
            .first()
        )

        employee = (
            db.query(Models.EmployeeInfo)
            .filter(Models.EmployeeInfo.employee_email == organization_general_info.primary_email)
            .first()
        )

        organization_general_info.primary_email = data.email
        organization_general_info.indexed_email_domain = domain

        employee.employee_email = data.email

        db.commit()

        encrypted_org_id = urlsafe_data_encoding_function(organization.id)

        email_data = {
            "recever_email": data.email,
            "subject": "Verify Your Email Address to Activate Your OrbitRMS Account",
            "body": VerifyEmailHtmlBody(
                VerifyEmailPydanticBody(
                    confirm_my_email=f"{FRONTEND_URL}/verification/verify-email?organization-id={encrypted_org_id}",
                    organization_name=organization_general_info.organization_name,
                )
            ),
        }

        email_instance = EmailSchema(**email_data)

        email_sender_function(email_instance, background_task)

        return {
            "success": SUCCESS.TRUE,
            "message": SUCCESS_MESSAGE.VERIFICATION_EMAIL_SENT_SUCCESSFULLY,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_RESENDING_EMAIL_VERIFICATION,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@adminOrgRoute.post(path="/reset/resend-onboarding-instruction")
@limiter.limit(API_RATE_LIMITING)
async def Resend_Onboarding_Instruction(
    request: Request,
    db: db_dependencies,
    data: ResendVerificationMail,
    background_task: BackgroundTasks,
    token: str = Depends(verify_token),
    id: str = Query(..., alias="id"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.UNAUTHORIZED, "success": SUCCESS.FALSE},
            )

        admin_id = token["admin_id"]
        session_id = token["session_id"]
        admin_signature = token["admin_signature"]

        admin = (
            db.query(Models.Admin)
            .options(joinedload(Models.Admin.admin_sessions))
            .filter(Models.Admin.id == admin_id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.INVALID_SESSION, "success": SUCCESS.FALSE},
            )

        find_organization = (
            db.query(Models.OrganizationGeneralInfo)
            .filter(Models.OrganizationGeneralInfo.primary_email == data.email)
            .first()
        )

        if not find_organization:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": ERROR_MESSAGE.NO_ORGANIZATION_FOUND,
                    "success": SUCCESS.FALSE,
                    "owner_email": find_organization.primary_email,
                },
            )

        organization = (
            db.query(Models.Organization)
            .join(Models.OrganizationGeneralInfo)
            .filter(Models.Organization.id == id)
            .first()
        )

        employee = (
            db.query(Models.User)
            .join(Models.EmployeeInfo, Models.EmployeeInfo.user_id == Models.User.id)
            .filter(
                Models.User.organization_id == organization.id,
                Models.EmployeeInfo.employee_email == data.email,
            )
            .first()
        )

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": ERROR_MESSAGE.EMPLOYEE_NOT_FOUND,
                    "success": SUCCESS.FALSE,
                },
            )

        encrypted_user_id = urlsafe_data_encoding_function(employee.id)

        reset_password_token = generatePasswordResetToken()

        employee.reset_password_token = reset_password_token

        encrypted_token = urlsafe_data_encoding_function(reset_password_token)

        email_data = {
            "recever_email": data.email,
            "subject": "Complete Your Account Setup – Create Your Password",
            "body": CreatePasswordHtmlBody(
                CreatePasswordPydanticBody(
                    user_name="",
                    organization_name=organization.general_info.organization_name,
                    create_password_link=f"{FRONTEND_URL}/auth/create-password?user-id={encrypted_user_id}&token={encrypted_token}",
                )
            ),
        }

        email_instance = EmailSchema(**email_data)

        email_sender_function(email_instance, background_task)

        db.commit()

        return {
            "message": SUCCESS_MESSAGE.VERIFICATION_EMAIL_SENT_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_RESENDING_EMAIL_VERIFICATION,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@adminOrgRoute.post(path="/delete/delete-organization")
@limiter.limit(API_RATE_LIMITING)
async def Delete_Organization(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    id: str = Query(..., alias="id"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.UNAUTHORIZED, "success": SUCCESS.FALSE},
            )

        admin_id = token["admin_id"]
        session_id = token["session_id"]
        admin_signature = token["admin_signature"]

        admin = (
            db.query(Models.Admin)
            .options(joinedload(Models.Admin.admin_sessions))
            .filter(Models.Admin.id == admin_id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.INVALID_SESSION, "success": SUCCESS.FALSE},
            )

        organization = db.query(Models.Organization).filter(Models.Organization.id == id).first()

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.NO_ORGANIZATION_FOUND,
                    "success": SUCCESS.FALSE,
                },
            )

        db.delete(organization)
        db.commit()

        return {
            "message": SUCCESS_MESSAGE.ORGANIZATION_DELETED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_DELETING_ORGANIZATION,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )
