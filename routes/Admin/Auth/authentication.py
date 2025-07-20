from fastapi import APIRouter, status, HTTPException, BackgroundTasks, Request, Query
from RateLimiting import limiter
import os
from dotenv import load_dotenv
from Database.Database import db_dependencies
from PydanticModels.Admin.AdminAuthenticationModel import AdminSignInPayload, AdminVerifyOTP
from SqlModels import Models
from Helper.jwtHelper import verify_password, hash_passwords, create_jwt_token
from ErrorMessages.AuthErrorMessage import (
    ADMIN_SIGN_IN_INVALID_CREDENTIALS,
    ADMIN_RESET_LIMIT_EXCEEDED,
    ADMIN_SIGN_IN_SUCCESS_MESSAGE,
    ADMIN_SIGN_IN_ERROR_MESSAGE,
    ADMIN_NOT_FOUND,
    INSUFFICIENT_DATA,
    ADMIN_OTP_VERIFY_SUCCESS_MESSAGE,
    INVALID_OTP,
)
from Database.CacheDatabase import cache_database
from Helper.createModelInstance import cerate_model_instance
from Constant.constant import MAX_RESET_ATTEMPTS, RESET_TTL_SECONDS
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from Helper.helper import (
    generateAdminAccessCode,
    generateAdminSignature,
    urlsafe_data_encoding_function,
    urlsafe_data_decoding_function,
    get_client_ip,
    hash_fingerprint,
)
from user_agents import parse as parse_user_agent
from Email.HtmlEmailBody import NewAdminLoginGeneratedOtp
from Helper.emailSender import EmailSchema, email_sender_function

from Database.CacheDatabase import cache_database

load_dotenv(override=True)


API_RATE_LIMITING = os.getenv("API_RATE_LIMITING")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ORBITRMS_OWNER_EMAIL = os.getenv("ORBITRMS_OWNER_EMAIL")


adminAuthRoute = APIRouter(prefix="/app/v1/admin/auth", tags=["admin"])


# @adminAuthRoute.post("/feed-admin-data", status_code=status.HTTP_200_OK)
# async def FeedAminInTheDatabase(db: db_dependencies):
#     try:
#         admin = db.query(Models.Admin).filter(Models.Admin.email == ADMIN_EMAIL).first()
#         if admin:
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail={
#                     "message": "All Ready Exist",
#                     "success": False,
#                 },
#             )

#         hash_password = hash_passwords(ADMIN_PASSWORD)

#         admin = Models.Admin(email=ADMIN_EMAIL, password=hash_password, admin_signature="")

#         db.add(admin)
#         db.commit()
#         db.refresh(admin)

#         return {
#             "message": ADMIN_SIGN_IN_SUCCESS_MESSAGE,
#             "success": True,
#         }

#     except HTTPException as http_exception:
#         raise http_exception
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail={
#                 "message": ADMIN_SIGN_IN_ERROR_MESSAGE,
#                 "success": False,
#                 "error": str(e),
#             },
#         )


@adminAuthRoute.post("/sign-in", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Admin_Panel_Sign_In_Function(
    request: Request,
    db: db_dependencies,
    data: AdminSignInPayload,
    background_task: BackgroundTasks,
):
    try:
        cache_key = f"sign_in_attempt_{data.email}"
        expiry_key = f"{cache_key}_expiry"
        count = await cache_database.incr(cache_key) or 0
        count = int(count)

        if count == 1:
            await cache_database.expire(cache_key, RESET_TTL_SECONDS)

        if count > MAX_RESET_ATTEMPTS:
            expiry_time_str = await cache_database.get(expiry_key)

            if not expiry_time_str:

                expiry_time = datetime.now(ZoneInfo("UTC")) + timedelta(seconds=RESET_TTL_SECONDS)
                await cache_database.set(expiry_key, expiry_time.isoformat(), ex=RESET_TTL_SECONDS)
                return {
                    "message": ADMIN_RESET_LIMIT_EXCEEDED,
                    "success": False,
                    "data": {
                        "expiry_time": expiry_time,
                    },
                }
            else:
                expiry_time = datetime.fromisoformat(expiry_time_str)
                return {
                    "message": ADMIN_RESET_LIMIT_EXCEEDED,
                    "success": False,
                    "data": {
                        "expiry_time": expiry_time,
                    },
                }

        admin = db.query(Models.Admin).filter(Models.Admin.email == data.email).first()

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": ADMIN_SIGN_IN_INVALID_CREDENTIALS,
                    "success": False,
                },
            )

        check_password = verify_password(
            plain_password=data.password, hashed_password=admin.password
        )

        if not check_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ADMIN_SIGN_IN_INVALID_CREDENTIALS, "success": False},
            )

        await cache_database.delete(cache_key)
        await cache_database.delete(expiry_key)

        otp_code = generateAdminAccessCode(6)
        admin_signature = generateAdminSignature()
        hashed_otp_code = hash_passwords(otp_code)

        cache_database_key = f"admin_otp_{admin.id}_{admin_signature}"

        await cache_database.set(cache_database_key, hashed_otp_code, ex=600)

        encrypted_admin_id = urlsafe_data_encoding_function(admin.id)

        email_data = {
            "recever_email": ORBITRMS_OWNER_EMAIL,
            "subject": "Verify Your Email Address to Activate Your OrbitRMS Account",
            "body": NewAdminLoginGeneratedOtp(otp_code),
        }

        email_instance = EmailSchema(**email_data)

        email_sender_function(email_instance, background_task)

        return {
            "message": ADMIN_SIGN_IN_SUCCESS_MESSAGE,
            "success": True,
            "data": {
                "admin_signature": admin_signature,
                "id": encrypted_admin_id,
            },
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ADMIN_SIGN_IN_ERROR_MESSAGE,
                "success": False,
                "error": str(e),
            },
        )


@adminAuthRoute.post("/verify-otp", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Admin_Panel_Verify_OTP_Function(
    request: Request,
    db: db_dependencies,
    data: AdminVerifyOTP,
    id: str = Query(..., alias="id"),
    signature: str = Query(..., alias="signature"),
):
    try:
        if not id or not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": INSUFFICIENT_DATA, "success": False},
            )
        decrypted_admin_id = urlsafe_data_decoding_function(id)

        admin = db.query(Models.Admin).filter(Models.Admin.id == decrypted_admin_id).first()

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": ADMIN_NOT_FOUND, "success": False},
            )

        cache_database_key = f"admin_otp_{decrypted_admin_id}_{signature}"
        stored_hash = await cache_database.get(cache_database_key)

        if stored_hash and verify_password(data.otp, stored_hash):
            # success: delete OTP key and proceed
            await cache_database.delete(cache_database_key)
        else:
            # invalid or expired
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": INVALID_OTP, "success": False},
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

        device_fingerprint = f"{browser }|{user_agent.os.family}|{user_agent.device.family}|{ip}"

        hash_device_fingerprint = hash_fingerprint(device_fingerprint)

        existing_session = (
            db.query(Models.OrbitAdminSessions)
            .filter(
                Models.OrbitAdminSessions.fingerprint == hash_device_fingerprint,
                Models.OrbitAdminSessions.admin_id == admin.id,
            )
            .first()
        )

        if existing_session:
            existing_session.updated_at = datetime.now(ZoneInfo("UTC"))

            db.commit()
            db.refresh(existing_session)
            admin_sessions = existing_session
        else:
            admin_signature = generateAdminSignature()
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
                "admin_signature": admin_signature,
            }
            admin_sessions = cerate_model_instance(
                data=device_info, model=Models.OrbitAdminSessions, fields=["-admin_id"]
            )
            admin_sessions.admin_id = admin.id
            db.add(admin_sessions)
            db.commit()
            db.refresh(admin_sessions)

        sub = {
            "admin_id": admin.id,
            "session_id": admin_sessions.id,
            "admin_signature": admin_sessions.admin_signature,
        }

        token = create_jwt_token(data=sub)

        return {
            "message": ADMIN_OTP_VERIFY_SUCCESS_MESSAGE,
            "success": True,
            "data": {
                "authenticationToken": token,
            },
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ADMIN_SIGN_IN_ERROR_MESSAGE,
                "success": False,
                "error": str(e),
            },
        )
