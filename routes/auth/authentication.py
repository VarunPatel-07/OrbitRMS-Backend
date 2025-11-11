import json
import os
from datetime import datetime, timedelta
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
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func
from user_agents import parse as parse_user_agent

from Config.EnvConfig import EnvConfig
from Constant.constant import MAX_RESET_ATTEMPTS, RESET_TTL_SECONDS
from Database.CacheDatabase import cache_database
from Database.Database import db_dependencies
from Email.HtmlEmailBody import (
    NewClientInquiryMailHtmlBody,
    ResetPasswordHtmlBody,
    VerifyEmailHtmlBody,
)
from Helper.createModelInstance import cerate_model_instance
from Helper.emailSender import EmailSchema, email_sender_function
from Helper.helper import (
    filter_fields,
    generatePasswordResetToken,
    get_client_ip,
    hash_fingerprint,
    model_to_filtered_dict,
    urlsafe_data_decoding_function,
    urlsafe_data_encoding_function,
)
from Helper.jwtHelper import create_jwt_token, hash_passwords, verify_password
from Middleware.UserAuthenticator import UserAuthenticatorMiddleware
from Middleware.verifyToken import verify_token
from PydanticModels.authentication.AuthenticationModels import (
    CreatePassword,
    PasswordResetPydanticModel,
    RegisterOrganizationInfo,
    ResendVerificationMail,
    SignIn,
    VerifyMetaTag,
)
from PydanticModels.HelperPydanticModel import (
    NewClientInquiryMailPydanticBody,
    VerifyEmailPydanticBody,
)
from RateLimiting import limiter
from SqlModels import Models

load_dotenv(override=True)

FRONTEND_URL = EnvConfig.FRONTEND_URL.strip()

API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING

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
                VerifyEmailPydanticBody(
                    confirm_my_email=f"{FRONTEND_URL}/verification/verify-email?organization-id={encrypted_org_id}",
                    organization_name=organization_info.organization_name,
                )
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
@authRoutes.post(path="/password/set-password", status_code=status.HTTP_201_CREATED)
@limiter.limit(API_RATE_LIMITING)
async def create_password(
    request: Request,
    db: db_dependencies,
    password: CreatePassword,
    user_id: str = Query(..., alias="user-id"),
    token: str = Query(..., alias="token"),
    type: str = Query(..., alias="type"),
):
    try:
        decrypted_user_id = urlsafe_data_decoding_function(user_id)

        user = db.query(Models.User).filter(Models.User.id == decrypted_user_id).first()

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

        decrypted_token = urlsafe_data_decoding_function(token)

        compare_token = decrypted_token == user.reset_password_token

        if compare_token:

            check_password = verify_password(
                plain_password=password.password, hashed_password=user.password
            )

            if check_password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "New password must be different from the old one.",
                        "success": False,
                    },
                )

            hash_password = hash_passwords(password.password)

            user.password = hash_password
            user.password_created = True
            user.reset_password_token = ""
            db.commit()
            db.refresh(user)

            return {
                "message": f"the password is {type} successfully",
                "success": True,
            }
        else:
            return {
                "message": "This link is no longer valid. Please try again.",
                "success": False,
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
        cache_key = f"sign_in_attempt_{user_info.email}"
        count = await cache_database.incr(cache_key) or 0
        count = int(count)

        if count == 1:
            await cache_database.expire(cache_key, RESET_TTL_SECONDS)

        if count > MAX_RESET_ATTEMPTS:
            return {
                "message": "Reset limit exceeded. Please wait.",
                "success": False,
                "data": {
                    "expiry_time": datetime.now(ZoneInfo("UTC"))
                    + timedelta(seconds=RESET_TTL_SECONDS),
                },
            }

        user = (
            db.query(Models.User)
            .join(Models.EmployeeInfo, Models.EmployeeInfo.user_id == Models.User.id)
            .filter(Models.EmployeeInfo.employee_email == user_info.email)
            .first()
        )

        if not user:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid Email Or Password", "success": False},
            )

        check_password = verify_password(
            plain_password=user_info.password, hashed_password=user.password
        )

        if not check_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid Email Or Password", "success": False},
            )

        await cache_database.delete(cache_key)

        organization = (
            db.query(Models.Organization)
            .filter(Models.Organization.id == user.organization_id)
            .first()
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
        if user.reset_password_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "You’re currently resetting your password. Complete it before logging in.",
                    "success": False,
                },
            )

        ip = get_client_ip(request)
        # Getting The Full UserAgent String
        full_user_agent_string = request.headers.get("user-agent", "unknown")

        user_agent = parse_user_agent(full_user_agent_string)

        # Now Getting The "sec_ch_ua" User Agent String

        sec_ch_ua_string = request.headers.get("sec-ch-ua", "").lower()

        browser = user_agent.browser.family

        if "brave" in sec_ch_ua_string:
            browser = "Brave"

        device_fingerprint = f"{browser}|{user_agent.os.family}|{user_agent.device.family}|{ip}"

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

            db.commit()
            db.refresh(existing_session)
            user_sessions = existing_session
        else:

            device_info = {
                "ip_address": ip,
                "browser": browser,
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
            "data": {
                "authenticationToken": token,
                "organization_created": organization.organization_created,
                "organization_id": encrypted_org_id,
                "organization_general_info": model_to_filtered_dict(
                    organization.general_info,
                    [
                        "organization_name",
                        "organization_profile_picture",
                        "portal_url",
                        "portal_slug",
                    ],
                ),
            },
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


def build_permission_tree(associated_permissions):
    """
    Recursively build permission tree with nested sub-modules
    """
    permissions_data = []

    for assoc_perm in associated_permissions:
        if not assoc_perm.parent_module_id:  # Only root level modules
            perm_dict = {
                "module_label": assoc_perm.module_label,
                "is_active": assoc_perm.is_active,
                "permissions": [
                    {
                        "label": perm.label,
                        "is_allowed": perm.is_allowed,
                    }
                    for perm in assoc_perm.permissions
                ],
                "sub_modules": build_sub_modules(assoc_perm.sub_modules),
            }
            permissions_data.append(perm_dict)

    return permissions_data


def build_sub_modules(sub_modules):
    """
    Recursively build sub-modules
    """
    sub_modules_data = []

    for sub_module in sub_modules:
        sub_dict = {
            "module_label": sub_module.module_label,
            "is_active": sub_module.is_active,
            "permissions": [
                {
                    "label": perm.label,
                    "is_allowed": perm.is_allowed,
                }
                for perm in sub_module.permissions
            ],
            "sub_modules": (
                build_sub_modules(sub_module.sub_modules) if sub_module.sub_modules else []
            ),
        }
        sub_modules_data.append(sub_dict)

    return sub_modules_data


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
        maintenance_mode = db.query(Models.MaintenanceMode).first()

        if maintenance_mode and maintenance_mode.is_active:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                    "data": jsonable_encoder(model_to_filtered_dict(maintenance_mode)),
                },
            )

        user_id = token["user_id"]

        session_id = token["session_id"]

        user = (
            db.query(Models.User)
            .options(
                joinedload(Models.User.personal_info),
                joinedload(Models.User.employee_info)
                .joinedload(Models.EmployeeInfo.employee_role)
                .joinedload(Models.ConfigRoleModule.associated_permissions)
                .joinedload(Models.RoleAssociatedPermissionModule.permissions),
                joinedload(Models.User.employee_info)
                .joinedload(Models.EmployeeInfo.employee_role)
                .joinedload(Models.ConfigRoleModule.associated_permissions)
                .joinedload(Models.RoleAssociatedPermissionModule.sub_modules)
                .joinedload(Models.RoleAssociatedPermissionModule.permissions),
                joinedload(Models.User.organization).joinedload(Models.Organization.general_info),
                joinedload(Models.User.organization).joinedload(
                    Models.Organization.organization_settings
                ),
            )
            .filter(Models.User.id == user_id)
            .first()
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": ("Unable To Find User With This ID"),
                    "success": False,
                },
            )

        if not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": ("Account is deactivated. Access denied."),
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

        organization = user.organization
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

        encrypted_org_id = urlsafe_data_encoding_function(organization.id)

        permissions_data = []
        if user.employee_info and user.employee_info.employee_role:
            permissions_data = build_permission_tree(
                user.employee_info.employee_role.associated_permissions
            )

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
                    "general_info": (
                        model_to_filtered_dict(organization.general_info)
                        if organization.general_info
                        else None
                    ),
                    "organization_settings": (
                        model_to_filtered_dict(organization.organization_settings)
                        if organization.organization_settings
                        else None
                    ),
                    "status": organization.status,
                    "organization_created": organization.organization_created,
                    "created_at": organization.created_at,
                    "updated_at": organization.updated_at,
                },
                "roles_permissions": {
                    "id": user.employee_info.employee_role.id,
                    "role_name": user.employee_info.employee_role.role_name,
                    "is_editable": user.employee_info.employee_role.is_editable,
                    "permissions": permissions_data,
                },
            },
            "encrypted_org_id": encrypted_org_id if not organization.organization_created else None,
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


@authRoutes.post("/logout", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def HandelLogoutApi(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
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

        find_session = db.query(Models.Sessions).filter(Models.Sessions.id == session_id).first()

        db.delete(find_session)
        db.commit()

        return {
            "message": "Logout successfully",
            "success": True,
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable to log out the user at this moment.",
                "success": False,
                "error": str(e),
            },
        )


@authRoutes.post("/password-reset/request")
@limiter.limit(API_RATE_LIMITING)
async def HandelPasswordReset(
    request: Request,
    db: db_dependencies,
    data: PasswordResetPydanticModel,
    background_task: BackgroundTasks,
):
    try:
        email = data.email.lower().strip()
        cache_key = f"password_reset-${email}"

        count = await cache_database.incr(cache_key)

        if count > MAX_RESET_ATTEMPTS:
            return {
                "message": "Reset limit exceeded. Please wait.",
                "success": False,
                "data": {
                    "expiry_time": datetime.now(ZoneInfo("UTC"))
                    + timedelta(seconds=RESET_TTL_SECONDS),
                },
            }

        if count == 1:
            await cache_database.expire(cache_key, RESET_TTL_SECONDS)

        employee_info = (
            db.query(Models.EmployeeInfo)
            .filter(Models.EmployeeInfo.employee_email == data.email)
            .first()
        )
        if not employee_info:

            count = count + 1
            return {
                "message": "User Found",
                "success": False,
            }

        user = db.query(Models.User).filter(Models.User.id == employee_info.user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "user not found", "success": False},
            )

        await cache_database.delete(cache_key)
        encrypted_user_id = urlsafe_data_encoding_function(user.id)

        reset_password_token = generatePasswordResetToken()

        user.reset_password_token = reset_password_token

        encrypted_token = urlsafe_data_encoding_function(reset_password_token)

        db.commit()
        db.refresh(user)

        email_data = {
            "recever_email": data.email,
            "subject": "Reset Your Password for Your OrbitRMS Account",
            "body": ResetPasswordHtmlBody(
                f"{FRONTEND_URL}/auth/reset-password?user-id={encrypted_user_id}&token={encrypted_token}"
            ),
        }

        email_instance = EmailSchema(**email_data)

        email_sender_function(email_instance, background_task)

        return {
            "message": "Mail Sent Successfully",
            "success": True,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable to log out the user at this moment.",
                "success": False,
                "error": str(e),
            },
        )


@authRoutes.get("/maintenance/check-maintenance-mode")
@limiter.limit(API_RATE_LIMITING)
async def Check_For_The_Maintenance_Mode(
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
        maintenance_mode = db.query(Models.MaintenanceMode).first()

        if maintenance_mode and maintenance_mode.is_active:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Maintenance Mode Is Active Now",
                    "success": False,
                    "data": jsonable_encoder(model_to_filtered_dict(maintenance_mode)),
                },
            )
        user_id = token["user_id"]

        session_id = token["session_id"]

        user = (
            db.query(Models.User)
            .options(
                joinedload(Models.User.organization).joinedload(Models.Organization.general_info),
            )
            .filter(Models.User.id == user_id)
            .first()
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": ("Unable To Find User With This ID"),
                    "success": False,
                },
            )

        if not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": ("Account is deactivated. Access denied."),
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
            "data": {"portal_slug": organization.general_info.portal_slug},
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


@authRoutes.post("/resend-verification-mail", status_code=status.HTTP_201_CREATED)
@limiter.limit(API_RATE_LIMITING)
async def create_organization(
    request: Request,
    db: db_dependencies,
    background_task: BackgroundTasks,
    data: ResendVerificationMail,
):
    try:

        organization_info = (
            db.query(Models.OrganizationGeneralInfo)
            .filter(Models.OrganizationGeneralInfo.primary_email == data.email)
            .first()
        )

        if not organization_info:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "No Such Organization Found",
                    "success": False,
                },
            )

        encrypted_org_id = urlsafe_data_encoding_function(organization_info.organization_id)

        email_data = {
            "recever_email": organization_info.primary_email,
            "subject": "Verify Your Email Address to Activate Your OrbitRMS Account",
            "body": VerifyEmailHtmlBody(
                f"{FRONTEND_URL}/verification/verify-email?organization-id={encrypted_org_id}"
            ),
        }

        email_instance = EmailSchema(**email_data)

        email_sender_function(email_instance, background_task)

        return {"success": True, "message": "Email Send Successfully"}
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


@authRoutes.post("/employee/password/reset-instructions", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def reset_password_instructions(
    request: Request,
    db: db_dependencies,
    data: ResendVerificationMail,
    background_task: BackgroundTasks,
    user: dict = Depends(UserAuthenticatorMiddleware),
    user_id: str = Query(..., alias="user-id"),
):
    try:
        employee = (
            db.query(Models.User)
            .options(joinedload(Models.User.personal_info))
            .filter(Models.User.id == user_id)
            .first()
        )

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Employee Not Found",
                    "success": False,
                },
            )

        organization = (
            db.query(Models.Organization)
            .options(joinedload(Models.Organization.general_info))
            .filter(Models.Organization.id == employee.organization_id)
            .first()
        )

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Organization Not Found",
                    "success": False,
                },
            )

        encrypted_user_id = urlsafe_data_encoding_function(employee.id)

        reset_password_token = generatePasswordResetToken()

        employee.reset_password_token = reset_password_token

        encrypted_token = urlsafe_data_encoding_function(reset_password_token)

        db.query(Models.Sessions).filter(Models.Sessions.user_id == employee.id).delete()

        db.commit()
        db.refresh(employee)

        email_data = {
            "recever_email": data.email,
            "subject": "Reset Your Password for Your OrbitRMS Account",
            "body": NewClientInquiryMailHtmlBody(
                NewClientInquiryMailPydanticBody(
                    reset_password_link=f"{FRONTEND_URL}/auth/reset-password?user-id={encrypted_user_id}&token={encrypted_token}",
                    organization_name=organization.general_info.organization_name,
                    user_name=employee.personal_info.full_name,
                )
            ),
        }

        email_instance = EmailSchema(**email_data)

        email_sender_function(email_instance, background_task)

        return {
            "message": "Reset Password Link Sent SuccessFully",
            "success": True,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error Accrued While Password Reset Instruction",
                "success": False,
                "error": str(e),
            },
        )
