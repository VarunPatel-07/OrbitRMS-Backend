import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup
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
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func
from user_agents import parse as parse_user_agent

from Database.Database import db_dependencies
from Email.HtmlEmailBody import VerifyEmailHtmlBody
from Helper.createModelInstance import cerate_model_instance
from Helper.emailSender import EmailSchema, email_sender_function
from Helper.helper import (
    filter_fields,
    get_client_ip,
    hash_fingerprint,
    model_to_filtered_dict,
    urlsafe_data_decoding_function,
    urlsafe_data_encoding_function,
)
from Helper.jwtHelper import create_jwt_token, hash_passwords, verify_password
from Middleware.verifyToken import verify_token
from PydanticModels.authentication.AuthenticationModels import (
    CreatePassword,
    RegisterOrganizationInfo,
    SignIn,
    VerifyMetaTag,
)
from RateLimiting import limiter
from SqlModels import Models

load_dotenv(override=True)

FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip()

API_RATE_LIMITING = os.getenv("API_RATE_LIMITING")

authRoutes = APIRouter(prefix="/app/v1/auth", tags=["auth"])


#
# ? The Api For The Sign UP And Creating a New Organization
#
@authRoutes.post("/sign-up", status_code=status.HTTP_201_CREATED)
@limiter.limit(API_RATE_LIMITING)
async def create_organization(
    request: Request,
    organization_info: RegisterOrganizationInfo,
    db: db_dependencies,
    background_task: BackgroundTasks,
):
    try:
        find_organization = (
            db.query(Models.OrganizationGeneralInfo)
            .filter(Models.OrganizationGeneralInfo.primary_email == organization_info.primary_email)
            .first()
        )
        check_for_the_email_domain = (
            db.query(Models.OrganizationGeneralInfo)
            .filter(
                func.substring_index(Models.OrganizationGeneralInfo.primary_email, "@", -1)
                == organization_info.primary_email.split("@")[1]
            )
            .first()
        )

        if check_for_the_email_domain:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "The Provided Email Domain Is Already In Use",
                    "success": False,
                    "owner_email": find_organization.primary_email if find_organization else None,
                },
            )

        if find_organization:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "The Provided Email Is Already In Use",
                    "success": False,
                    "owner_email": find_organization.primary_email,
                },
            )

        create_org = Models.Organization(status=True)

        db.add(create_org)
        db.commit()
        db.refresh(create_org)

        organization = cerate_model_instance(
            model=Models.OrganizationGeneralInfo,
            data=organization_info,
            fields=["-country_info"],
        )
        user_info = Models.User(password="")
        user_info.organization_id = create_org.id
        db.add(user_info)
        db.commit()
        db.refresh(user_info)
        user_employee_info = Models.EmployeeInfo(
            status="Confirmed",
            organization_name=organization_info.organization_name,
            employee_code="",
            department="",
            designation="",
            employee_email=organization_info.primary_email,
        )
        user_employee_info.user_id = user_info.id
        db.add(user_employee_info)
        db.commit()
        db.refresh(user_employee_info)
        organization.organization_id = create_org.id

        organization.country_info = json.dumps(
            organization_info.country_info.dict()
            if hasattr(organization_info.country_info, "dict")
            else organization_info.country_info
        )

        db.add(organization)
        db.commit()
        db.refresh(organization)

        encrypted_org_id = urlsafe_data_encoding_function(create_org.id)

        email_data = {
            "recever_email": organization_info.primary_email,
            "subject": "Verify Your Email Address to Activate Your OrbitRMS Account",
            "body": VerifyEmailHtmlBody(
                f"{FRONTEND_URL}/verification/verify-email?organization-id={encrypted_org_id}"
            ),
        }

        email_instance = EmailSchema(**email_data)

        send_mail = email_sender_function(email_instance, background_task)

        return {
            "success": True,
            "title": "Organization Created",
            "message": f"Your organization has been successfully created. A confirmation email with further details has been sent to {user_employee_info.employee_email}. Please check your inbox and follow the instructions to complete the setup.",
            "email_status": send_mail,
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error Accrued While Adding Employee",
                "success": False,
                "error": str(e),
            },
        )


#
# ? The Api To Create An Strong Password For You Organization
#
@authRoutes.post(path="/create-password", status_code=status.HTTP_201_CREATED)
@limiter.limit(API_RATE_LIMITING)
async def create_password(
    request: Request,
    db: db_dependencies,
    password: CreatePassword,
    user_id: str = Query(..., alias="user-id"),
):
    try:
        decrypted_user_id = urlsafe_data_decoding_function(user_id)

        user = db.query(Models.User).filter(Models.User.id == decrypted_user_id).first()

        hash_password = hash_passwords(password.password)

        organization = (
            db.query(Models.Organization)
            .filter(Models.Organization.id == user.organization_id)
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "user not found", "success": False},
            )
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "organization not found", "success": False},
            )
        if not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Account is deactivated. Access denied.",
                    "success": False,
                },
            )

        if not organization.status:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        if not user.password_created:

            user.password = hash_password
            user.password_created = True
            db.commit()
            db.refresh(user)

            return {
                "message": "the password is created successfully",
                "success": True,
                "password_already_created": False,
            }
        else:
            return {
                "message": "the password is already created",
                "success": True,
                "password_already_created": True,
            }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "there was an error while creating a password",
                "success": False,
                "error": str(e),
            },
        )


#
# ? The Api To Sign-In in Your Organization
#
@authRoutes.post(path="/sign-in", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def sing_in(db: db_dependencies, user_info: SignIn, request: Request):
    try:
        employee_info = (
            db.query(Models.EmployeeInfo)
            .filter(Models.EmployeeInfo.employee_email == user_info.email)
            .first()
        )
        if not employee_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid Email Or Password", "success": False},
            )
        user = db.query(Models.User).filter(Models.User.id == employee_info.user_id).first()

        organization = (
            db.query(Models.Organization)
            .filter(Models.Organization.id == user.organization_id)
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "user not found", "success": False},
            )
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "organization not found", "success": False},
            )
        if not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Account is deactivated. Access denied.",
                    "success": False,
                },
            )

        if not organization.status:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        check_password = verify_password(
            plain_password=user_info.password, hashed_password=user.password
        )

        if not check_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid Email Or Password", "success": False},
            )
        ip = get_client_ip(request)
        user_agent_string = request.headers.get("user-agent", "unknown")
        user_agent = parse_user_agent(user_agent_string)

        device_fingerprint = f"{user_agent_string}-{ip}"

        hash_device_fingerprint = hash_fingerprint(device_fingerprint)

        existing_session = (
            db.query(Models.Sessions)
            .filter(
                Models.Sessions.fingerprint == hash_device_fingerprint,
                Models.Sessions.user_id == user.id,
            )
            .first()
        )

        if existing_session:
            existing_session.updated_at = datetime.now(ZoneInfo("UTC"))
            print("finger print found")
            db.commit()
            db.refresh(existing_session)
            user_sessions = existing_session
        else:
            print("finger print not found")
            device_info = {
                "ip_address": ip,
                "browser": user_agent.browser.family,
                "browser_version": user_agent.browser.version_string,
                "os": user_agent.os.family,
                "os_version": user_agent.os.version_string,
                "device_type": user_agent.device.family,
                "is_mobile": user_agent.is_mobile,
                "is_tablet": user_agent.is_tablet,
                "is_pc": user_agent.is_pc,
                "is_bot": user_agent.is_bot,
                "fingerprint": hash_device_fingerprint,
            }
            user_sessions = cerate_model_instance(
                data=device_info, model=Models.Sessions, fields=["-user_id"]
            )
            user_sessions.user_id = user.id
            db.add(user_sessions)
            db.commit()
            db.refresh(user_sessions)

        sub = {"user_id": user.id, "session_id": user_sessions.id}

        token = create_jwt_token(data=sub)

        encrypted_org_id = urlsafe_data_encoding_function(organization.id)

        return {
            "message": "User Sign In Successfully",
            "success": True,
            "authenticationToken": token,
            "organization_created": organization.organization_created,
            "organization_id": encrypted_org_id,
            "organization_general_info": model_to_filtered_dict(
                organization.general_info,
                ["organization_name", "organization_profile_picture", "portal_url", "portal_slug"],
            ),
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": str(e),
                "message": "error accrued while signing in",
                "success": False,
            },
        )


#
# ? The Api To Fetch All The Logged In Devices Of The User Your Organization
#
@authRoutes.get(path="/fetch-sessions", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_sessions(request: Request, db: db_dependencies, token: str = Depends(verify_token)):
    try:
        #
        # *  We Will Firstly Check For The User's Authentication
        #
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

        # We Will Also Check For The Relevant Session That This Particular Session Exists Or Not

        if not any(session.id == session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
                headers={"WWW-Authenticate": "Bearer"},
            )

        #
        # *  Once The User Is Authenticated Then We Will Move Further
        #

        _data = [filter_fields(data) for data in user.sessions]

        return {
            "message": "user verified successfully",
            "success": True,
            "data": _data,
            "current_session_id": session_id,
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while verifying user",
                "success": False,
                "error": str(e),
            },
        )


#
# ? The Api To Delete An Specific Sessions
#
@authRoutes.delete(path="/delete-session", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_sessions(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    session_id: str = Query(..., alias="session_id"),
):
    try:
        #
        # *  We Will Firstly Check For The User's Authentication
        #
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        current_session_id = token["session_id"]

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

        # We Will Also Check For The Relevant Session That This Particular Session Exists Or Not

        if not any(session.id == current_session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
                headers={"WWW-Authenticate": "Bearer"},
            )

        #
        # *  Once The User Is Authenticated Then We Will Move Further
        #

        find_session = db.query(Models.Sessions).filter(Models.Sessions.id == session_id).first()

        db.delete(find_session)
        db.commit()

        return {
            "message": "Session Deleted successfully",
            "success": True,
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while verifying user",
                "success": False,
                "error": str(e),
            },
        )


#
# ? The Api To Verify The Organization
#
@authRoutes.get(path="/verify-user", status_code=status.HTTP_200_OK)
async def verify_user(request: Request, db: db_dependencies, token: str = Depends(verify_token)):
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
            .options(
                joinedload(Models.User.personal_info),
                joinedload(Models.User.employee_info),
                joinedload(Models.User.organization).joinedload(Models.Organization.general_info),
                joinedload(Models.User.organization).joinedload(Models.Organization.address),
                joinedload(Models.User.organization).joinedload(Models.Organization.contact_info),
                joinedload(Models.User.organization).joinedload(Models.Organization.about_info),
                joinedload(Models.User.organization).joinedload(
                    Models.Organization.organization_settings
                ),
                joinedload(Models.User.sessions),
            )
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
                        else "Unable To Find User With This ID"
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

        organization = (
            db.query(Models.Organization)
            .filter(Models.Organization.id == user.organization_id)
            .first()
        )
        if not organization or not organization.status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Organization is deactivated. Access denied."
                        if user.account_status
                        else "Organization not found"
                    ),
                    "success": False,
                },
            )

        organization = user.organization

        return {
            "message": "user verified successfully",
            "success": True,
            "data": {
                "user": {
                    "employee_info": model_to_filtered_dict(user.employee_info),
                    "personal_info": (
                        model_to_filtered_dict(user.personal_info) if user.personal_info else None
                    ),
                },
                "organization": {
                    "id": organization.id,
                    "general_info": model_to_filtered_dict(organization.general_info),
                    "address": model_to_filtered_dict(organization.address[0]),
                    "contact_info": organization.contact_info,
                    "about_info": model_to_filtered_dict(organization.about_info[0]),
                    "organization_settings": model_to_filtered_dict(
                        organization.organization_settings[0]
                    ),
                    "status": organization.status,
                    "organization_created": organization.organization_created,
                    "created_at": organization.created_at,
                    "updated_at": organization.updated_at,
                },
            },
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while verifying user",
                "success": False,
                "error": str(e),
            },
        )


@authRoutes.post("/verify-meta-tag", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def verify_meta_tag(request: Request, data: VerifyMetaTag):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(data.website_url)
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        meta_tag = soup.find("meta", attrs={"name": data.meta_name})

        if not meta_tag:
            return {
                "data": {
                    "meta_found": False,
                    "expected_value": data.meta_value,
                    "actual_value": "",
                    "match": False,
                },
                "success": False,
                "message": "Meta Tag Not Found",
            }

        if meta_tag and "content" in meta_tag.attrs:
            actual_value = meta_tag.get("content", "")

            verified = actual_value == data.meta_value

            return {
                "data": {
                    "meta_found": True,
                    "expected_value": data.meta_value,
                    "actual_value": actual_value,
                    "match": verified,
                },
                "success": True,
                "message": "Meta Tag Verified Successfully",
            }
        return {"error": "Meta tag not found"}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error Accrued While Verifying The Meta Tag",
                "success": False,
                "error": str(e),
            },
        )
