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

from config.EnvConfig import EnvConfig
from database.CacheDatabase import cache_database
from database.Database import db_dependencies
from jobs.backgroundHandler.DataSeederHelper import ClientInquiryInitiator
from jobs.backgroundHandler.initialDataSeeder import (
    client_form_field_initial_data_seeder,
    department_data_initial_data_seeder,
    designation_initial_data_seeder,
    project_status_initial_data_seeder,
    roles_permission_initial_data_seeder_function,
)
from jobs.backgroundTasks.emailDispatcher.Background_Mail_Initiator import (
    OnboardingCompletedMailSending,
)
from mailer.HtmlEmailBody import CreatePasswordHtmlBody
from middleware.UserAuthenticator import UserAuthenticatorMiddleware
from models.pydantic.HelperPydanticModel import (
    CreatePasswordPydanticBody,
)
from models.pydantic.Organizations.organizations import (
    OnboardingOrganization,
)
from models.sql import Models
from RateLimiting import limiter
from utils.helper.createModelInstance import cerate_model_instance
from utils.helper.emailSender import EmailSchema, email_sender_function
from utils.helper.helper import (
    filter_fields,
    generate_api_secrets_api_key,
    generatePasswordResetToken,
    update_model_data,
    urlsafe_data_decoding_function,
    urlsafe_data_encoding_function,
)
from utils.helper.jwtHelper import hash_passwords

load_dotenv(override=True)

orgRouter = APIRouter(prefix="/app/v1/organization", tags=["organization"])


FRONTEND_URL = EnvConfig.FRONTEND_URL.strip()

API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING


#
#
# ? ------------ Api To Verify The Organization ---------------------
#
#


@orgRouter.get("/verify-organization", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def verify_organization(
    request: Request,
    db: db_dependencies,
    background_task: BackgroundTasks,
    organization_id: str = Query(..., alias="organization-id"),
):
    try:
        decrypted_org_id = urlsafe_data_decoding_function(organization_id)

        organization = (
            db.query(Models.OrganizationGeneralInfo)
            .filter(Models.OrganizationGeneralInfo.organization_id == decrypted_org_id)
            .first()
        )
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Organization Not Found", "success": False},
            )
        if not organization.email_verified:
            organization.email_verified = True

            user = (
                db.query(Models.User)
                .join(Models.EmployeeInfo, Models.EmployeeInfo.user_id == Models.User.id)
                .filter(Models.EmployeeInfo.employee_email == organization.primary_email)
                .first()
            )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "message": "User Not Found",
                        "success": False,
                    },
                )

            encrypted_user_id = urlsafe_data_encoding_function(user.id)

            reset_password_token = generatePasswordResetToken()

            hash_token = hash_passwords(reset_password_token)

            password_cache_key = f"set_reset_password_token_{user.id}"
            await cache_database.set(password_cache_key, hash_token, ex=600)

            encrypted_token = urlsafe_data_encoding_function(reset_password_token)

            email_data = {
                "recever_email": organization.primary_email,
                "subject": "Complete Your Account Setup – Create Your Password",
                "body": CreatePasswordHtmlBody(
                    CreatePasswordPydanticBody(
                        user_name="",
                        organization_name=organization.organization_name,
                        create_password_link=f"{FRONTEND_URL}/auth/create-password?user-id={encrypted_user_id}&token={encrypted_token}",
                    )
                ),
            }

            email_instance = EmailSchema(**email_data)

            email_sender_function(email_instance, background_task)

            config_module = Models.ConfigModule()
            config_module.organization_id = decrypted_org_id

            db.add(config_module)
            db.commit()

            db.refresh(config_module)
            db.refresh(user)

            background_task.add_task(
                roles_permission_initial_data_seeder_function, db, decrypted_org_id
            )
            background_task.add_task(
                designation_initial_data_seeder, db, decrypted_org_id, organization.industry_slug
            )
            background_task.add_task(
                department_data_initial_data_seeder,
                db,
                decrypted_org_id,
                organization.industry_slug,
            )
            background_task.add_task(project_status_initial_data_seeder, db, decrypted_org_id)
            background_task.add_task(client_form_field_initial_data_seeder, db, decrypted_org_id)

            return {
                "message": "Organization Is Verified Successfully",
                "success": True,
                "data": {
                    "alreadyVerified": False,
                },
            }
        else:
            user_info = (
                db.query(Models.EmployeeInfo)
                .filter(Models.EmployeeInfo.employee_email == organization.primary_email)
                .first()
            )

            encrypted_user_id = urlsafe_data_encoding_function(user_info.user_id)

            # todo need to add email
            return {
                "message": "Organization already Verified",
                "success": True,
                "data": {
                    "alreadyVerified": True,
                },
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


# @orgRouter.get("/data-feeder", status_code=status.HTTP_200_OK)
# @limiter.limit(API_RATE_LIMITING)
# async def verify_organization(
#     request: Request,
#     db: db_dependencies,
#     background_task: BackgroundTasks,
#     organization_id: str = Query(..., alias="organization-id"),
# ):
#     try:
#         decrypted_org_id = organization_id

#         organization = (
#             db.query(Models.OrganizationGeneralInfo)
#             .filter(Models.OrganizationGeneralInfo.organization_id == decrypted_org_id)
#             .first()
#         )
#         if not organization:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail={"message": "Organization Not Found", "success": False},
#             )

#         user = (
#             db.query(Models.User)
#             .join(Models.EmployeeInfo, Models.EmployeeInfo.user_id == Models.User.id)
#             .filter(Models.EmployeeInfo.employee_email == organization.primary_email)
#             .first()
#         )
#         if not user:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail={
#                     "message": "User Not Found",
#                     "success": False,
#                 },
#             )

#         background_task.add_task(
#             roles_permission_initial_data_seeder_function, db, decrypted_org_id
#         )

#         return {
#             "message": "Organization Is Verified Successfully",
#             "success": True,
#             "data": {
#                 "alreadyVerified": False,
#             },
#         }

#     except HTTPException as http_exception:
#         raise http_exception
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail={
#                 "message": "Error Accrued While Adding Employee",
#                 "success": False,
#                 "error": str(e),
#             },
#         )


#
#
# ? ------------ Api For The Onboarding An Organization ---------------------
#
#


@orgRouter.post("/onboard-organization", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def onboard_organization(
    request: Request,
    db: db_dependencies,
    data: OnboardingOrganization,
    background_task: BackgroundTasks,
    organization_id: str = Query(..., alias="organization-id"),
):
    try:
        organization_id = urlsafe_data_decoding_function(organization_id)
        organization = (
            db.query(Models.Organization).filter(Models.Organization.id == organization_id).first()
        )
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Organization Not Found",
                    "success": False,
                },
            )

        organization.status = data.status
        organization.organization_created = True

        updated_general_info = update_model_data(
            db=db,
            model=Models.OrganizationGeneralInfo,
            model_id=organization_id,
            id_field="organization_id",
            updated_data=data.general_info,
        )

        fetch_admin_role = (
            db.query(Models.ConfigRoleModule)
            .join(Models.ConfigModule)
            .filter(
                Models.ConfigModule.organization_id == organization.id,
                Models.ConfigRoleModule.role_name == "Administrator",
            )
            .first()
        )

        user_info = (
            db.query(Models.EmployeeInfo)
            .filter(Models.EmployeeInfo.employee_email == data.general_info.primary_email)
            .first()
        )

        user_info.employee_role_id = fetch_admin_role.id

        db.add(user_info)

        updated_user_info = cerate_model_instance(
            model=Models.PersonalInfo,
            data=data.employee_profile_info,
            fields=["-normalized_full_name"],
        )

        normalized_full_name = func.regexp_replace(
            func.lower(
                func.regexp_replace(func.trim(data.employee_profile_info.full_name), r"\s+", " ")
            ),
            r"\s+",
            "",
        )

        updated_user_info.user_id = user_info.user_id
        updated_user_info.normalized_full_name = normalized_full_name
        db.add(updated_user_info)

        address = cerate_model_instance(model=Models.OrganizationAddress, data=data.address)
        address.organization_id = organization.id
        db.add(address)

        contact_info_arr = []

        for each_contact in data.contact_info:
            contact = cerate_model_instance(data=each_contact, model=Models.OrganizationContactInfo)
            contact.organization_id = organization.id

            contact_info_arr.append(contact)
        db.add_all(contact_info_arr)

        about_info = cerate_model_instance(model=Models.OrganizationAboutInfo, data=data.about_info)
        about_info.organization_id = organization.id
        db.add(about_info)

        organization_settings = cerate_model_instance(
            model=Models.OrganizationSettings, data=data.organization_settings
        )
        organization_settings.organization_id = organization.id
        db.add(organization_settings)

        db.commit()

        api_key, api_secret = generate_api_secrets_api_key()

        background_task.add_task(ClientInquiryInitiator, db, organization_id, api_key, api_secret)
        background_task.add_task(OnboardingCompletedMailSending, data, background_task)

        return {
            "message": f"successfully onboarded {data.general_info.organization_name} organization",
            "success": True,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while onboarding the organization",
                "error": str(e),
            },
        )


#
#
# ? ------------ Api To Fetch The Organization Info ---------------------
#
#


@orgRouter.get("/fetch-organization-info", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_organization_info(
    request: Request,
    db: db_dependencies,
    organization_id: str = Query(..., alias="organization_id"),
):
    try:

        organization_id = urlsafe_data_decoding_function(organization_id)

        organization = (
            db.query(Models.Organization)
            .options(
                joinedload(Models.Organization.general_info),
                joinedload(Models.Organization.address),
                joinedload(Models.Organization.contact_info),
                joinedload(Models.Organization.about_info),
                joinedload(Models.Organization.organization_settings),
            )
            .filter(Models.Organization.id == organization_id)
            .first()
        )

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Unable To Find Organization With This Organization Id",
                    "success": False,
                },
            )

        return {
            "success": True,
            "data": {
                "general_info": (
                    filter_fields(organization.general_info, ["-id", "-organization_id"])
                    if organization.general_info
                    else None
                ),
                "address": (
                    filter_fields(organization.address[0], ["-id", "-organization_id"])
                    if organization.address
                    else None
                ),
                "contact_info": (
                    filter_fields(organization.contact_info[0], ["-id", "-organization_id"])
                    if organization.contact_info
                    else None
                ),
                "about_info": (
                    filter_fields(organization.about_info[0], ["-id", "-organization_id"])
                    if organization.about_info
                    else None
                ),
                "organization_settings": (
                    filter_fields(
                        organization.organization_settings[0], ["-id", "-organization_id"]
                    )
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
                "message": "error while fetching the organization info",
                "error": str(e),
                "success": False,
            },
        )


#
#
# ? ------------ Api To Fetch The Reporting Managers ---------------------
#
#


@orgRouter.get("/fetch-reporting-manager", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_reporting_manager(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        fetch_all_users = (
            db.query(Models.User)
            .options(joinedload(Models.User.personal_info))
            .filter(Models.User.organization_id == user.organization_id)
            .all()
        )

        return {
            "success": True,
            "data": [
                (
                    {
                        **filter_fields(
                            each_user.personal_info,
                            ["last_name", "first_name", "middle_name", "user_id"],
                        ),
                        "full_name": f"{each_user.personal_info.first_name or ''} {each_user.personal_info.middle_name or ''} {each_user.personal_info.last_name or ''}".strip(),
                    }
                    if not getattr(each_user.personal_info, "full_name", "")
                    else filter_fields(
                        each_user.personal_info,
                        ["last_name", "first_name", "middle_name", "user_id", "full_name"],
                    )
                )
                for each_user in fetch_all_users
                if each_user.personal_info
            ],
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while fetching All The Reporting Manager",
                "error": str(e),
                "success": False,
            },
        )
