import os

from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from Database.Database import db_dependencies
from Email.HtmlEmailBody import WelcomeMailForNewlyAddedEmployee
from Helper.createModelInstance import cerate_model_instance
from Helper.emailSender import EmailSchema, email_sender_function
from Helper.helper import filter_fields, urlsafe_data_encoding_function
from Helper.jwtHelper import hash_passwords
from Middleware.verifyToken import verify_token
from PydanticModels.HelperPydanticModel import WelcomeEmployeeMailModel
from PydanticModels.Organizations.AddEditEmployeePydanticModal import (
    AddEditUserProfileModel,
)
from SqlModels import Models

load_dotenv(override=True)

SUPER_SECURE_HASH_PASSWORD = os.getenv("SUPER_SECURE_HASH_PASSWORD", "").strip()
FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip()


alignable_for_child_info = [
    "Married",
    "Divorced",
    "Widowed",
    "Prefer not to say",
]

employee_router = APIRouter(prefix="/app/v1/employee", tags=["employee"])


@employee_router.post("/add", status_code=status.HTTP_200_OK)
async def handel_add_user_function(
    db: db_dependencies,
    data: AddEditUserProfileModel,
    background_task: BackgroundTasks,
    token: str = Depends(verify_token),
    organization_id: str = Query(..., alias="organization-id"),
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

        user_id = token["user_id"]
        user = db.query(Models.User).filter(Models.User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Unable To Find User With This ID",
                    "success": False,
                },
            )

        organization_info = (
            db.query(Models.Organization)
            .options(joinedload(Models.Organization.general_info))
            .filter(Models.Organization.id == organization_id)
            .first()
        )

        if not organization_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Unable To Find The Organization With This ID",
                    "success": False,
                },
            )

        existing_user = db.query(Models.PersonalInfo).filter(
            func.lower(Models.PersonalInfo.full_name) == data.personal_info.full_name
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Employee With This Name Already Exist",
                    "success": False,
                },
            )

        hash_password = hash_passwords(SUPER_SECURE_HASH_PASSWORD)

        new_user = Models.User(password=hash_password)
        new_user.organization_id = organization_id
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        personal_info = cerate_model_instance(
            model=Models.PersonalInfo, data=data.personal_info, fields=["-user_id"]
        )

        personal_info.user_id = new_user.id
        db.add(personal_info)
        db.commit()
        db.refresh(personal_info)

        reporting_to_user = (
            db.query(Models.User)
            .filter(Models.User.id == data.employee_info.reporting_to.id)
            .first()
        )
        if not reporting_to_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": f"Reporting to user ID {data.employee_info.reporting_to.id} does not exist.",
                    "success": False,
                },
            )

        employee_info_data = data.employee_info.dict(exclude={"employee_role", "reporting_to"})

        employee_info = cerate_model_instance(
            model=Models.EmployeeInfo,
            data=employee_info_data,
            fields=["-employee_role_id", "-user_id", "-reporting_to_id", "-reporting_to"],
        )
        employee_info.employee_role_id = data.employee_info.employee_role.role_id
        employee_info.reporting_to_id = data.employee_info.reporting_to.id
        employee_info.user_id = new_user.id

        db.add(employee_info)
        db.commit()
        db.refresh(employee_info)

        personal_contact_info_data = data.personal_contact_info.dict(exclude={"emergency_contact"})

        personal_contact_info = cerate_model_instance(
            model=Models.PersonalContactInfo, data=personal_contact_info_data, fields=["-user_id"]
        )
        personal_contact_info.user_id = new_user.id
        db.add(personal_contact_info)
        db.commit()
        db.refresh(personal_contact_info)

        emergency_contact_array = []
        for emergency_contact in data.personal_contact_info.emergency_contact:
            contact = cerate_model_instance(
                model=Models.EmergencyContact, data=emergency_contact, fields=["-contact_id"]
            )
            contact.contact_id = personal_contact_info.id
            emergency_contact_array.append(contact)

        db.add_all(emergency_contact_array)
        db.commit()

        family_info_data = data.family_info.dict(exclude={"children"})

        family_info = cerate_model_instance(
            model=Models.FamilyInfo, data=family_info_data, fields=["-user_id"]
        )
        family_info.user_id = new_user.id
        db.add(family_info)
        db.commit()
        db.refresh(family_info)

        if data.family_info.marital_status in alignable_for_child_info:

            children_array = []
            for each_child in data.family_info.children:
                child = cerate_model_instance(
                    model=Models.Children, data=each_child, fields=["-family_info_id"]
                )
                child.family_info_id = family_info.id
                children_array.append(child)
            db.add_all(children_array)
            db.commit()

        current_address = cerate_model_instance(model=Models.Address, data=data.current_address)
        db.add(current_address)
        db.commit()
        db.refresh(current_address)
        new_user.current_address_id = current_address.id
        new_user.same_as_current_address = data.same_as_current_address

        if not data.same_as_current_address:
            permanent_address = cerate_model_instance(
                model=Models.Address, data=data.permanent_address
            )
            db.add(permanent_address)
            db.commit()
            db.refresh(permanent_address)
            new_user.permanent_address_id = permanent_address.id
        db.commit()
        db.refresh(new_user)

        social_links_array = []
        for link in data.social_links:
            social_link = cerate_model_instance(
                model=Models.SocialLinks, data=link, fields=["-user_id"]
            )
            social_link.user_id = new_user.id
            social_links_array.append(social_link)
        db.add_all(social_links_array)
        db.commit()

        encrypted_user_id = urlsafe_data_encoding_function(new_user.id)

        emil_body_data = {
            "user_name": data.personal_info.full_name,
            "organization_name": organization_info.general_info.organization_name,
            "create_password_link": f"{FRONTEND_URL}/auth/create-password?user-id={encrypted_user_id}",
        }

        email_data = {
            "recever_email": data.employee_info.employee_email,
            "subject": f"Welcome {data.personal_info.full_name} to {organization_info.general_info.organization_name} – We're excited to have you onboard!",
            "body": WelcomeMailForNewlyAddedEmployee(WelcomeEmployeeMailModel(**emil_body_data)),
        }

        email_instance = EmailSchema(**email_data)

        email_sender_function(email_instance, background_task)

        return {
            "message": "successfully added the user",
            "success": True,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while Adding The User",
                "error": str(e),
                "success": False,
            },
        )


@employee_router.get("/fetch-profile", status_code=status.HTTP_200_OK)
async def handel_fetch_profile_info(
    db: db_dependencies,
    token: str = Depends(verify_token),
    employee_id: str = Query(..., alias="employee_id"),
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

        user_id = token["user_id"]
        user = db.query(Models.User).filter(Models.User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Unable To Find User With This ID",
                    "success": False,
                },
            )

        user_info = (
            db.query(Models.User)
            .options(
                joinedload(Models.User.personal_info),
                joinedload(Models.User.employee_info)
                .joinedload(Models.EmployeeInfo.reporting_manager)
                .joinedload(Models.User.personal_info),
                joinedload(Models.User.employee_info).joinedload(Models.EmployeeInfo.employee_role),
                joinedload(Models.User.personal_contact_info).joinedload(
                    Models.PersonalContactInfo.emergency_contacts
                ),
                joinedload(Models.User.family_info).joinedload(Models.FamilyInfo.children),
                joinedload(Models.User.current_address),
                joinedload(Models.User.permanent_address),
                joinedload(Models.User.social_link),
            )
            .filter(Models.User.id == employee_id)
            .first()
        )

        return {
            "message": "user verified successfully",
            "success": True,
            "data": {
                **filter_fields(
                    user_info,
                    fields=[
                        "-password",
                        "-personal_info",
                        "-personal_contact_info",
                        "-family_info",
                        "-employee_info",
                    ],
                ),
                "employee_info": {
                    **filter_fields(user_info.employee_info, fields=["-reporting_manager"]),
                    "reporting_manager": {
                        **filter_fields(
                            user_info.employee_info.reporting_manager,
                            fields=[
                                "id",
                            ],
                        ),
                        **(
                            filter_fields(
                                user_info.employee_info.reporting_manager.personal_info[0],
                                fields=[
                                    "-id",
                                    "first_name",
                                    "last_name",
                                    "middle_name",
                                    "profile_picture",
                                    "profile_picture_bg",
                                    "full_name",
                                    "gender",
                                ],
                            )
                            if user_info.employee_info.reporting_manager.personal_info
                            else {}
                        ),
                    },
                },
                "personal_info": (
                    filter_fields(user_info.personal_info[0]) if user_info.personal_info else {}
                ),
                "personal_contact_info": (
                    filter_fields(user_info.personal_contact_info[0])
                    if user_info.personal_contact_info
                    else {}
                ),
                "family_info": (
                    filter_fields(user_info.family_info[0]) if user_info.family_info else {}
                ),
            },
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while Fetching The User Info",
                "error": str(e),
                "success": False,
            },
        )
