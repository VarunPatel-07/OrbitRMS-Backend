import math
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

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
from user_agents import parse as parse_user_agent
from constants.constant import SUCCESS
from config.EnvConfig import EnvConfig
from constants.constant import (
    MAX_RESET_ATTEMPTS,
    RESEND_OTP_AVAILABLE_AT_DEFAULT_TIME,
    RESET_TTL_SECONDS,
)
from database.CacheDatabase import cache_database
from database.Database import db_dependencies
from mailer.HtmlEmailBody import NewAdminLoginGeneratedOtp
from middleware.verifyToken import verify_token
from models.pydantic.Admin.AdminAuthenticationModel import (
    AdminSignInPayload,
    AdminVerifyOTP,
)
from models.sql import Models
from middleware.RateLimiting import limiter
from utils.helper.createModelInstance import cerate_model_instance
from utils.helper.emailSender import EmailSchema, email_sender_function
from utils.helper.helper import (
    generateAdminAccessCode,
    generateAdminSignature,
    get_client_ip,
    hash_fingerprint,
    urlsafe_data_decoding_function,
    urlsafe_data_encoding_function,
)
from utils.helper.jwtHelper import create_jwt_token, hash_passwords, verify_password
from utils.responseMessages import ERROR_MESSAGE, SUCCESS_MESSAGE

load_dotenv(override=True)


API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING
ADMIN_EMAIL = EnvConfig.ADMIN_EMAIL
ADMIN_PASSWORD = EnvConfig.ADMIN_PASSWORD
ORBITRMS_OWNER_EMAIL = EnvConfig.ORBITRMS_OWNER_EMAIL


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

#         admin = Models.Admin(email=ADMIN_EMAIL, password=hash_password)

#         db.add(admin)
#         db.commit()
#         db.refresh(admin)

#         return {
#             "message": ADMIN_SIGN_IN_SUCCESS_MESSAGE,
#             "success": SUCCESS.TRUE,
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
                    "message": ERROR_MESSAGE.ADMIN_RESET_LIMIT_EXCEEDED,
                    "success": SUCCESS.FALSE,
                    "data": {
                        "expiry_time": expiry_time,
                    },
                }
            else:
                expiry_time = datetime.fromisoformat(expiry_time_str)
                return {
                    "message": ERROR_MESSAGE.ADMIN_RESET_LIMIT_EXCEEDED,
                    "success": SUCCESS.FALSE,
                    "data": {
                        "expiry_time": expiry_time,
                    },
                }

        admin = db.query(Models.Admin).filter(Models.Admin.email == data.email).first()

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": ERROR_MESSAGE.ADMIN_SIGN_IN_INVALID_CREDENTIALS,
                    "success": SUCCESS.FALSE,
                },
            )

        check_password = verify_password(
            plain_password=data.password, hashed_password=admin.password
        )

        if not check_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": ERROR_MESSAGE.ADMIN_SIGN_IN_INVALID_CREDENTIALS,
                    "success": SUCCESS.FALSE,
                },
            )

        await cache_database.delete(cache_key)
        await cache_database.delete(expiry_key)

        otp_code = generateAdminAccessCode(6)
        admin_signature = generateAdminSignature()
        hashed_otp_code = hash_passwords(otp_code)

        cache_database_key = f"admin_otp_{admin.id}_{admin_signature}"

        await cache_database.set(
            cache_database_key, hashed_otp_code, ex=RESEND_OTP_AVAILABLE_AT_DEFAULT_TIME
        )

        encrypted_admin_id = urlsafe_data_encoding_function(admin.id)

        email_data = {
            "recever_email": ORBITRMS_OWNER_EMAIL,
            "subject": "Verify Your Email Address to Activate Your OrbitRMS Account",
            "body": NewAdminLoginGeneratedOtp(otp_code),
        }

        email_instance = EmailSchema(**email_data)

        email_sender_function(email_instance, background_task)

        otp_expiry_key = f"{admin_signature}_otp_expiry"
        otp_resend_available_at = await cache_database.get(otp_expiry_key)
        otp_expiry_time: datetime

        if not otp_resend_available_at:

            otp_expiry_time = datetime.now(ZoneInfo("UTC")) + timedelta(
                seconds=RESEND_OTP_AVAILABLE_AT_DEFAULT_TIME
            )
            await cache_database.set(
                otp_expiry_key, otp_expiry_time.isoformat(), ex=RESEND_OTP_AVAILABLE_AT_DEFAULT_TIME
            )
        else:
            otp_expiry_time = datetime.fromisoformat(otp_resend_available_at)

        return {
            "message": SUCCESS_MESSAGE.ADMIN_SIGN_IN_SUCCESS_MESSAGE,
            "success": SUCCESS.TRUE,
            "data": {
                "admin_signature": admin_signature,
                "id": encrypted_admin_id,
                "resend_available_at": otp_expiry_time,
            },
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ADMIN_SIGN_IN_ERROR_MESSAGE,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )


@adminAuthRoute.post("/otp/verify-otp", status_code=status.HTTP_200_OK)
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
                detail={"message": ERROR_MESSAGE.INSUFFICIENT_DATA, "success": SUCCESS.FALSE},
            )
        decrypted_admin_id = urlsafe_data_decoding_function(id)

        admin = db.query(Models.Admin).filter(Models.Admin.id == decrypted_admin_id).first()

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        cache_database_key = f"admin_otp_{decrypted_admin_id}_{signature}"
        stored_hash = await cache_database.get(cache_database_key)
        if not stored_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": ERROR_MESSAGE.INVALID_OTP, "success": SUCCESS.FALSE},
            )
        if not verify_password(data.otp, stored_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": ERROR_MESSAGE.INVALID_OTP, "success": SUCCESS.FALSE},
            )

        await cache_database.delete(cache_database_key)

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

        token = create_jwt_token(data=sub, expires_date=timedelta(hours=3))

        otp_expiry_key = f"{signature}_otp_expiry"
        otp_expiry = await cache_database.get(otp_expiry_key)

        if otp_expiry:

            await cache_database.delete(otp_expiry_key)

        return {
            "message": SUCCESS_MESSAGE.ADMIN_OTP_VERIFY_SUCCESS_MESSAGE,
            "success": SUCCESS.TRUE,
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
                "message": ERROR_MESSAGE.ADMIN_SIGN_IN_ERROR_MESSAGE,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )


@adminAuthRoute.get("/verify-user", status_code=status.HTTP_200_OK)
async def Admin_Panel_Verify_User_Function(
    db: db_dependencies,
    token: str = Depends(verify_token),
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

        return {
            "message": SUCCESS_MESSAGE.ADMIN_VERIFIED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": {
                "admin_id": admin.id,
                "email": admin.email,
            },
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while Verifying Admin",
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@adminAuthRoute.post("/otp/re-send-otp", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Re_Send_Admin_Panel_Access_Otp(
    request: Request,
    db: db_dependencies,
    background_task: BackgroundTasks,
    id: str = Query(..., alias="id"),
    signature: str = Query(..., alias="signature"),
):
    try:
        url_decoded_admin_id = urlsafe_data_decoding_function(id)

        admin = db.query(Models.Admin).filter(Models.Admin.id == url_decoded_admin_id).first()

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": ERROR_MESSAGE.INVALID_CREDENTIAL, "success": SUCCESS.FALSE},
            )

        otp_expiry_key = f"{signature}_otp_expiry"

        otp_resend_available_at = await cache_database.get(otp_expiry_key)

        if otp_resend_available_at:
            otp_expiry_time_left = datetime.fromisoformat(otp_resend_available_at)

            time_left = math.floor(
                (otp_expiry_time_left - datetime.now(timezone.utc)).total_seconds()
            )

            if time_left > 60:
                time_left = math.ceil(time_left / 60)

            if time_left > 0:
                return {
                    "message": f"Please Try After {time_left}{'s'if time_left>60 else 'm'}",
                    "success": SUCCESS.FALSE,
                    "data": {
                        "resend_available_at": otp_expiry_time_left,
                    },
                }
        else:

            cache_database_key = f"admin_otp_{admin.id}_{signature}"

            otp_code = generateAdminAccessCode(6)

            hashed_otp_code = hash_passwords(otp_code)

            await cache_database.set(cache_database_key, hashed_otp_code, ex=600)

            email_data = {
                "recever_email": ORBITRMS_OWNER_EMAIL,
                "subject": "Verify Your Email Address to Activate Your OrbitRMS Account",
                "body": NewAdminLoginGeneratedOtp(otp_code),
            }

            email_instance = EmailSchema(**email_data)

            email_sender_function(email_instance, background_task)

            otp_expiry_time: datetime

            if not otp_resend_available_at:

                otp_expiry_time = datetime.now(ZoneInfo("UTC")) + timedelta(
                    seconds=RESEND_OTP_AVAILABLE_AT_DEFAULT_TIME
                )
                await cache_database.set(
                    otp_expiry_key,
                    otp_expiry_time.isoformat(),
                    ex=RESEND_OTP_AVAILABLE_AT_DEFAULT_TIME,
                )

            return {
                "message": SUCCESS_MESSAGE.ADMIN_SIGN_IN_SUCCESS_MESSAGE,
                "success": SUCCESS.TRUE,
                "data": {
                    "resend_available_at": otp_expiry_time,
                },
            }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ADMIN_SIGN_IN_ERROR_MESSAGE,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )
