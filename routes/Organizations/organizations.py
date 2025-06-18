import os

from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import joinedload

from BackgroundDataHandler.initialDataSeeder import (
    department_data_initial_data_seeder,
    designation_initial_data_seeder,
    project_status_initial_data_seeder,
    roles_permission_initial_data_seeder_function,
)
from Database.Database import db_dependencies
from Email.HtmlEmailBody import CreatePasswordHtmlBody
from Helper.createModelInstance import cerate_model_instance
from Helper.emailSender import EmailSchema, email_sender_function
from Helper.helper import (
    filter_fields,
    model_to_filtered_dict,
    update_model_data,
    urlsafe_data_decoding_function,
    urlsafe_data_encoding_function,
)
from Middleware.verifyToken import verify_token
from PydanticModels.Organizations.organizations import (
    OnboardingOrganization,
)
from SqlModels import Models

load_dotenv(override=True)

orgRouter = APIRouter(prefix="/app/v1/organization", tags=["organization"])


FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip()


#
#
# ? ------------ Api To Verify The Organization ---------------------
#
#


@orgRouter.get("/verify-organization", status_code=status.HTTP_200_OK)
async def verify_organization(
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
            db.commit()
            db.refresh(organization)

            user_info = (
                db.query(Models.EmployeeInfo)
                .filter(Models.EmployeeInfo.employee_email == organization.primary_email)
                .first()
            )

            encrypted_user_id = urlsafe_data_encoding_function(user_info.user_id)

            email_data = {
                "recever_email": user_info.employee_email,
                "subject": "Complete Your Account Setup – Create Your Password",
                "body": CreatePasswordHtmlBody(
                    f"{FRONTEND_URL}/auth/create-password?user-id={encrypted_user_id}"
                ),
            }

            email_instance = EmailSchema(**email_data)

            email_sender_function(email_instance, background_task)

            config_module = Models.ConfigModule()
            config_module.organization_id = decrypted_org_id
            db.add(config_module)
            db.commit()
            db.refresh(config_module)

            background_task.add_task(
                roles_permission_initial_data_seeder_function, db, decrypted_org_id
            )
            background_task.add_task(designation_initial_data_seeder, db, decrypted_org_id)
            background_task.add_task(department_data_initial_data_seeder, db, decrypted_org_id)
            background_task.add_task(project_status_initial_data_seeder, db, decrypted_org_id)

            return {
                "message": "Organization Is Verified Successfully",
                "success": True,
                "alreadyVerified": False,
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
                "alreadyVerified": True,
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
#
# ? ------------ Api For The Onboarding An Organization ---------------------
#
#


@orgRouter.post("/onboard-organization", status_code=status.HTTP_200_OK)
async def onboard_organization(
    db: db_dependencies,
    data: OnboardingOrganization,
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

        db.commit()
        db.refresh(organization)

        updated_general_info = update_model_data(
            db=db,
            model=Models.OrganizationGeneralInfo,
            model_id=organization_id,
            id_field="organization_id",
            updated_data=data.general_info,
        )

        user_info = (
            db.query(Models.EmployeeInfo)
            .filter(Models.EmployeeInfo.employee_email == data.general_info.primary_email)
            .first()
        )

        updated_user_info = cerate_model_instance(
            model=Models.PersonalInfo,
            data=data.employee_profile_info,
        )

        updated_user_info.user_id = user_info.user_id
        db.add(updated_user_info)
        db.commit()

        address = cerate_model_instance(model=Models.OrganizationAddress, data=data.address)
        address.organization_id = organization.id
        db.add(address)
        db.commit()

        contact_info_arr = []

        for each_contact in data.contact_info:
            contact = cerate_model_instance(data=each_contact, model=Models.OrganizationContactInfo)
            contact.organization_id = organization.id
            db.add(contact)
            db.commit()

            contact_info_arr.append(contact)

        about_info = cerate_model_instance(model=Models.OrganizationAboutInfo, data=data.about_info)
        about_info.organization_id = organization.id
        db.add(about_info)
        db.commit()

        organization_settings = cerate_model_instance(
            model=Models.OrganizationSettings, data=data.organization_settings
        )
        organization_settings.organization_id = organization.id
        db.add(organization_settings)
        db.commit()

        return {
            "message": f"successfully onboarded {data.general_info.organization_name} organization",
            "success": True,
            "organization": {
                "status": organization.status,
                "organization_created": organization.organization_created,
                "general_info": model_to_filtered_dict(
                    updated_general_info, ["-id", "-organization_id"]
                ),
                "address": model_to_filtered_dict(address, ["-id", "-organization_id"]),
                "contact_info": [
                    model_to_filtered_dict(_contact_info, ["-id", "-organization_id"])
                    for _contact_info in contact_info_arr
                ],
                "about_info": model_to_filtered_dict(about_info, ["-id", "-organization_id"]),
                "organization_settings": model_to_filtered_dict(
                    organization_settings, ["-id", "-organization_id"]
                ),
            },
            "updated_user_info": model_to_filtered_dict(
                updated_user_info, ["-id", "-organization_id"]
            ),
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
async def fetch_organization_info(
    db: db_dependencies, organization_id: str = Query(..., alias="organization_id")
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
                    "message": "Unable To Find Organization With This Organization Id",
                    "success": False,
                },
            )

        organization_general_info = (
            db.query(Models.OrganizationGeneralInfo)
            .filter(Models.OrganizationGeneralInfo.organization_id == organization.id)
            .first()
        )
        organization_address = (
            db.query(Models.OrganizationAddress)
            .filter(Models.OrganizationAddress.organization_id == organization.id)
            .first()
        )

        contact_info = (
            db.query(Models.OrganizationContactInfo)
            .filter(Models.OrganizationContactInfo.organization_id == organization.id)
            .first()
        )
        about_info = (
            db.query(Models.OrganizationAboutInfo)
            .filter(Models.OrganizationAboutInfo.organization_id == organization.id)
            .first()
        )
        organization_settings = (
            db.query(Models.OrganizationSettings)
            .filter(Models.OrganizationSettings.organization_id == organization.id)
            .first()
        )

        return {
            "success": True,
            "data": {
                "general_info": (
                    model_to_filtered_dict(organization_general_info, ["-id", "-organization_id"])
                    if organization_general_info
                    else ""
                ),
                "address": (
                    model_to_filtered_dict(organization_address, ["-id", "-organization_id"])
                    if organization_address
                    else ""
                ),
                "contact_info": (
                    model_to_filtered_dict(contact_info, ["-id", "-organization_id"])
                    if contact_info
                    else ""
                ),
                "about_info": (
                    model_to_filtered_dict(about_info, ["-id", "-organization_id"])
                    if about_info
                    else ""
                ),
                "organization_settings": (
                    model_to_filtered_dict(organization_settings, ["-id", "-organization_id"])
                    if organization_settings
                    else ""
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
async def fetch_reporting_manager(db: db_dependencies, token: str = Depends(verify_token)):
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
