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
from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_
from sqlalchemy.orm import aliased, joinedload, selectinload
from sqlalchemy.sql import func

from Config.EnvConfig import EnvConfig
from Database.CacheDatabase import cache_database
from Database.Database import db_dependencies
from Email.HtmlEmailBody import WelcomeMailForNewlyAddedEmployee
from Helper.createModelInstance import cerate_model_instance
from Helper.emailSender import EmailSchema, email_sender_function
from Helper.helper import (
    filter_fields,
    generatePasswordResetToken,
    model_to_filtered_dict,
    urlsafe_data_encoding_function,
)
from Helper.jwtHelper import hash_passwords
from Middleware.UserAuthenticator import UserAuthenticatorMiddleware
from Middleware.verifyToken import verify_token
from PydanticModels.HelperPydanticModel import WelcomeEmployeeMailModel
from PydanticModels.Organizations.AddEditEmployeePydanticModal import (
    AddEditUserProfileModel,
)
from RateLimiting import limiter
from SqlModels import Models

from .EmployeeQueryFilters import apply_query_filter

load_dotenv(override=True)

SUPER_SECURE_HASH_PASSWORD = EnvConfig.SUPER_SECURE_HASH_PASSWORD.strip()

FRONTEND_URL = EnvConfig.FRONTEND_URL.strip()

API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING


alignable_for_child_info = [
    "Married",
    "Divorced",
    "Widowed",
    "Prefer not to say",
]

employee_router = APIRouter(prefix="/app/v1/employee", tags=["employee"])


def has_view_access(array_of_modules, label):
    for module in array_of_modules:
        if module.module_label == label:
            if any(
                permission.label == "view" and permission.is_allowed
                for permission in module.permissions or []
            ):
                return True

        if getattr(module, "sub_modules", None):
            if has_view_access(module.sub_modules or [], label):
                return True
    return False


@employee_router.post("/add", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def handel_add_user_function(
    request: Request,
    db: db_dependencies,
    data: AddEditUserProfileModel,
    background_task: BackgroundTasks,
    organization_id: str = Query(..., alias="organization-id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        organization_info = (
            db.query(Models.Organization).filter(Models.Organization.id == organization_id).first()
        )

        if not organization_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Unable To Find The Organization With This ID",
                    "success": False,
                },
            )

        def normalize_name(name: str) -> str:
            return " ".join(name.strip().split()).lower()

        existing_user = (
            db.query(Models.PersonalInfo)
            .join(Models.User, Models.PersonalInfo.user_id == Models.User.id)
            .filter(
                func.lower(Models.PersonalInfo.full_name)
                == normalize_name(data.personal_info.full_name),
                Models.User.organization_id == organization_id,
            )
            .first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Employee With This Name Already Exist",
                    "success": False,
                },
            )

        user_with_same_email = (
            db.query(Models.EmployeeInfo)
            .join(Models.User, Models.EmployeeInfo.user_id == Models.User.id)
            .filter(
                Models.EmployeeInfo.employee_email == data.employee_info.employee_email,
                Models.User.organization_id == organization_id,
            )
            .first()
        )

        if user_with_same_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "The Employee With This Mail Already Exist", "success": False},
            )

        user_with_same_employee_code = (
            db.query(Models.EmployeeInfo)
            .join(Models.User, Models.EmployeeInfo.user_id == Models.User.id)
            .filter(
                Models.EmployeeInfo.employee_code == data.employee_info.employee_code,
                Models.User.organization_id == organization_id,
            )
            .first()
        )

        if user_with_same_employee_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "The Employee With This Employee Code Exist", "success": False},
            )

        hash_password = hash_passwords(SUPER_SECURE_HASH_PASSWORD)

        new_user = Models.User(password=hash_password)
        new_user.organization_id = organization_id

        db.add(new_user)
        db.flush()

        # * We Will Add The Personal Info
        normalized_full_name = func.regexp_replace(
            func.lower(func.regexp_replace(func.trim(data.personal_info.full_name), r"\s+", " ")),
            r"\s+",
            "",
        )
        db.add(
            Models.PersonalInfo(
                user_id=new_user.id,
                normalized_full_name=normalized_full_name,
                **data.personal_info.dict(exclude={"user_id"}),
            )
        )

        # * Now We Are Validating The Reporting Manager And If It Exists Then We Will Add The Employee Info
        # * If Not Then We Will Raise An HTTP Exception

        if not data.employee_info.reporting_to or not getattr(
            data.employee_info.reporting_to, "id", None
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Reporting manager is required", "success": False},
            )

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

        db.add(
            Models.EmployeeInfo(
                **employee_info_data,
                user_id=new_user.id,
                reporting_to_id=data.employee_info.reporting_to.id,
                employee_role_id=data.employee_info.employee_role.role_id,
            )
        )

        personal_contact_info_data = data.personal_contact_info.dict(exclude={"emergency_contacts"})

        personal_contact_info = cerate_model_instance(
            model=Models.PersonalContactInfo,
            data=personal_contact_info_data,
            fields=[
                "-user_id",
            ],
        )
        personal_contact_info.user_id = new_user.id
        db.add(personal_contact_info)
        db.flush()

        emergency_contact_array = list(data.personal_contact_info.emergency_contacts or [])

        if emergency_contact_array:
            db.bulk_insert_mappings(
                Models.EmergencyContact,
                [
                    {
                        **_emergency_contact.dict(exclude={"contact_id", "id"}),
                        "contact_id": personal_contact_info.id,
                    }
                    for _emergency_contact in emergency_contact_array
                ],
            )

        # * Now We Are Adding The Family Info
        family_info_data = data.family_info.dict(exclude={"children"})

        family_info = Models.FamilyInfo(
            **family_info_data,
            user_id=new_user.id,
        )

        db.add(family_info)
        db.flush()

        if data.family_info.marital_status in alignable_for_child_info:

            children_array = list(data.family_info.children or [])

            if children_array:

                db.bulk_insert_mappings(
                    Models.Children,
                    [
                        {
                            **_child.dict(exclude={"family_info_id", "id"}),
                            "family_info_id": family_info.id,
                        }
                        for _child in children_array
                    ],
                )

        current_address = Models.Address(**data.current_address.dict())

        db.add(current_address)
        db.flush()

        new_user.current_address_id = current_address.id

        new_user.same_as_current_address = data.same_as_current_address

        if not data.same_as_current_address:

            permanent_address = Models.Address(**data.permanent_address.dict())

            db.add(permanent_address)
            db.flush()

            new_user.permanent_address_id = permanent_address.id

        social_links_array = []
        for link in data.social_link or []:
            if link.name and link.link and link.icon:
                social_links_array.append(link)
        if social_links_array:
            db.bulk_insert_mappings(
                Models.SocialLinks,
                [
                    {
                        **_link.dict(exclude={"user_id", "id"}),
                        "user_id": new_user.id,
                    }
                    for _link in social_links_array
                ],
            )
        db.commit()

        reset_password_token = generatePasswordResetToken()

        new_user.reset_password_token = reset_password_token

        encrypted_user_id = urlsafe_data_encoding_function(new_user.id)
        encrypted_token = urlsafe_data_encoding_function(reset_password_token)
        db.commit()
        db.refresh(new_user)

        emil_body_data = {
            "user_name": data.personal_info.full_name,
            "organization_name": organization_info.general_info.organization_name,
            "create_password_link": f"{FRONTEND_URL}/auth/create-password?user-id={encrypted_user_id}&token={encrypted_token}",
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
@limiter.limit(API_RATE_LIMITING)
async def handel_fetch_profile_info(
    request: Request,
    db: db_dependencies,
    employee_id: str = Query(..., alias="employee_id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        employee_data = (
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

        all_modules = (
            db.query(Models.RoleAssociatedPermissionModule)
            .filter(
                and_(
                    Models.RoleAssociatedPermissionModule.role_module_id
                    == user.employee_info.employee_role_id,
                    Models.RoleAssociatedPermissionModule.module_label == "employee_details",
                )
            )
            .options(
                joinedload(Models.RoleAssociatedPermissionModule.permissions),
                joinedload(Models.RoleAssociatedPermissionModule.sub_modules),
            )
            .all()
        )

        employee_data_neglect_field = [
            "-password",
            "-personal_info",
            "-personal_contact_info",
            "-family_info",
            "-employee_info",
        ]

        if not has_view_access(all_modules, "employee_address") and employee_id != user.id:
            employee_data_neglect_field = employee_data_neglect_field + [
                "-current_address",
                "-permanent_address",
                "-current_address_id",
                "-permanent_address_id",
            ]

        return {
            "message": "user verified successfully",
            "success": True,
            "use": user.id,
            "data": {
                **filter_fields(
                    employee_data,
                    fields=employee_data_neglect_field,
                ),
                "employee_info": (
                    {
                        **filter_fields(employee_data.employee_info, fields=["-reporting_manager"]),
                        "reporting_manager": (
                            {
                                **filter_fields(
                                    employee_data.employee_info.reporting_manager,
                                    fields=["id"],
                                ),
                                **(
                                    filter_fields(
                                        employee_data.employee_info.reporting_manager.personal_info,
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
                                    if employee_data.employee_info.reporting_manager
                                    and employee_data.employee_info.reporting_manager.personal_info
                                    else {}
                                ),
                            }
                            if employee_data.employee_info
                            and employee_data.employee_info.reporting_manager
                            else {}
                        ),
                    }
                    if (
                        has_view_access(all_modules, "employee_information")
                        or employee_id == user.id
                    )
                    else None
                ),
                "personal_info": (
                    filter_fields(employee_data.personal_info)
                    if (
                        (
                            employee_data.personal_info
                            and has_view_access(all_modules, "personal_information")
                        )
                        or employee_id == user.id
                    )
                    else None
                ),
                "personal_contact_info": (
                    filter_fields(employee_data.personal_contact_info)
                    if (
                        (
                            employee_data.personal_contact_info
                            and has_view_access(all_modules, "personal_contact_information")
                        )
                        or employee_id == user.id
                    )
                    else None
                ),
                "family_info": (
                    filter_fields(employee_data.family_info[0])
                    if (
                        (
                            employee_data.family_info
                            and has_view_access(all_modules, "family_information")
                        )
                        or employee_id == user.id
                    )
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
                "message": "error while Fetching The User Info",
                "error": str(e),
                "success": False,
            },
        )


@employee_router.get("/fetch-employee-profile", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def handel_fetch_profile_info(
    request: Request,
    db: db_dependencies,
    employee_id: str = Query(..., alias="employee_id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        employee_data = (
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

        employee_data_neglect_field = [
            "-password",
            "-personal_info",
            "-personal_contact_info",
            "-family_info",
            "-employee_info",
        ]

        return {
            "message": "user verified successfully",
            "success": True,
            "use": user.id,
            "data": {
                **filter_fields(
                    employee_data,
                    fields=employee_data_neglect_field,
                ),
                "employee_info": {
                    **filter_fields(employee_data.employee_info, fields=["-reporting_manager"]),
                    "reporting_manager": (
                        {
                            **filter_fields(
                                employee_data.employee_info.reporting_manager,
                                fields=["id"],
                            ),
                            **(
                                filter_fields(
                                    employee_data.employee_info.reporting_manager.personal_info,
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
                                if employee_data.employee_info.reporting_manager
                                and employee_data.employee_info.reporting_manager.personal_info
                                else {}
                            ),
                        }
                        if employee_data.employee_info
                        and employee_data.employee_info.reporting_manager
                        else {}
                    ),
                },
                "personal_info": (
                    filter_fields(employee_data.personal_info)
                    if employee_data.personal_info
                    else None
                ),
                "personal_contact_info": (
                    filter_fields(employee_data.personal_contact_info)
                    if employee_data.personal_contact_info
                    else None
                ),
                "family_info": (
                    filter_fields(employee_data.family_info[0])
                    if employee_data.family_info
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
                "message": "error while Fetching The User Info",
                "error": str(e),
                "success": False,
            },
        )


@employee_router.put("/edit", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def edit_employee_profile(
    request: Request,
    db: db_dependencies,
    data: AddEditUserProfileModel,
    employee_id: str = Query(..., alias="employee-id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        employee = (
            db.query(Models.User)
            .options(
                selectinload(Models.User.personal_info),
                selectinload(Models.User.employee_info),
                selectinload(Models.User.personal_contact_info).selectinload(
                    Models.PersonalContactInfo.emergency_contacts
                ),
                selectinload(Models.User.family_info).selectinload(Models.FamilyInfo.children),
                selectinload(Models.User.social_link),
            )
            .filter(Models.User.id == employee_id)
            .first()
        )

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Unable To Find Employee With This ID",
                    "success": False,
                },
            )

        existing_user = (
            db.query(Models.PersonalInfo)
            .filter(
                func.lower(Models.PersonalInfo.full_name) == data.personal_info.full_name,
                Models.PersonalInfo.user_id != employee_id,
            )
            .first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Employee With This Name Already Exist",
                    "success": False,
                },
            )
        # Now We Are Updating The Personal Info
        if employee.personal_info:
            update_employee_data = data.personal_info.dict(exclude_unset=True)
            normalized_full_name = func.regexp_replace(
                func.lower(
                    func.regexp_replace(func.trim(data.personal_info.full_name), r"\s+", " ")
                ),
                r"\s+",
                "",
            )
            update_employee_data["normalized_full_name"] = normalized_full_name
            db.query(Models.PersonalInfo).filter_by(user_id=employee.id).update(
                update_employee_data
            )

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
        db.query(Models.EmployeeInfo).filter(Models.EmployeeInfo.user_id == employee.id).update(
            {
                **data.employee_info.dict(exclude={"reporting_to", "employee_role"}),
                "employee_role_id": data.employee_info.employee_role.role_id,
                "reporting_to_id": data.employee_info.reporting_to.id,
            }
        )

        cache_data_key = [
            f"organization_roles_permissions_{user.organization_id}",
            f"organization_roles_permissions_fetch_role_{data.employee_info.employee_role.role_id}",
        ]

        for cache_key in cache_data_key:
            cached_data = await cache_database.get(cache_key)

            if cached_data:
                await cache_database.delete(cache_key)

        personal_contact_info_data = data.personal_contact_info.dict(exclude={"emergency_contacts"})

        contact_info_id = None

        if employee.personal_contact_info:
            db.query(Models.PersonalContactInfo).filter_by(user_id=employee.id).update(
                personal_contact_info_data
            )

            contact_info_id = employee.personal_contact_info.id
            print("in the if")

        else:
            new_personal_contact_info = Models.PersonalContactInfo(
                user_id=employee.id, **personal_contact_info_data
            )
            db.add(new_personal_contact_info)
            db.flush()
            contact_info_id = new_personal_contact_info.id

        print("contact_info_id", contact_info_id)

        existing_contacts = {
            str(c.id): c
            for c in db.query(Models.EmergencyContact)
            .filter(Models.EmergencyContact.contact_id == contact_info_id)
            .all()
        }

        contacts_to_update = []
        contacts_to_add = []

        for contact in data.personal_contact_info.emergency_contacts:

            if contact.id and contact.id in existing_contacts:
                contacts_to_update.append(contact)
            else:
                contacts_to_add.append(contact)

        if contacts_to_update:
            db.bulk_update_mappings(
                Models.EmergencyContact,
                [
                    {**_contact.dict(exclude={"contact_id", "id"}), "id": _contact.id}
                    for _contact in contacts_to_update
                ],
            )

        if contacts_to_add:
            db.bulk_insert_mappings(
                Models.EmergencyContact,
                [
                    {
                        **_contact.dict(exclude={"contact_id", "id"}),
                        "contact_id": contact_info_id,
                    }
                    for _contact in contacts_to_add
                ],
            )

        find_family_info = (
            db.query(Models.FamilyInfo).filter(Models.FamilyInfo.user_id == employee.id).first()
        )
        family_info_data = data.family_info.dict(exclude={"children"})
        if find_family_info:
            db.query(Models.FamilyInfo).filter(Models.FamilyInfo.user_id == employee.id).update(
                family_info_data
            )

        else:
            db.add(Models.FamilyInfo(user_id=employee.id, **family_info_data))

        if data.family_info.marital_status in alignable_for_child_info:

            existing_child_array = {
                str(child.id): child
                for child in db.query(Models.Children)
                .filter(Models.Children.family_info_id == find_family_info.id)
                .all()
            }

        children_array_to_update = []
        children_array_to_add = []

        for each_child in data.family_info.children:
            if each_child.id and str(each_child.id) in existing_child_array:
                children_array_to_update.append(each_child)
            else:
                children_array_to_add.append(each_child)

        if children_array_to_update:
            db.bulk_update_mappings(
                Models.Children,
                [
                    {**_child.dict(exclude={"family_info_id", "id"}), "id": _child.id}
                    for _child in children_array_to_update
                ],
            )

        if children_array_to_add:
            db.bulk_insert_mappings(
                Models.Children,
                [
                    {
                        **_child.dict(exclude={"family_info_id", "id"}),
                        "family_info_id": _child.id,
                    }
                    for _child in children_array_to_update
                ],
            )

        employee.same_as_current_address = data.same_as_current_address

        if employee.current_address_id:

            db.query(Models.Address).filter(
                Models.Address.id == employee.current_address_id
            ).update(data.current_address.dict())

        else:
            current_address = Models.Address(**data.current_address.dict())
            db.add(current_address)
            db.flush()

            employee.current_address_id = current_address.id

        if not data.same_as_current_address:

            if employee.permanent_address_id:

                db.query(Models.Address).filter(
                    Models.Address.id == employee.permanent_address_id
                ).update(data.permanent_address.dict())
            else:
                permanent_address = Models.Address(**data.current_address.dict())
                db.add(permanent_address)
                db.flush()

                employee.permanent_address_id = permanent_address.id

        elif employee.permanent_address_id:

            permanent_address = (
                db.query(Models.Address)
                .filter(Models.Address.id == employee.permanent_address_id)
                .first()
            )
            if permanent_address:
                db.delete(permanent_address)
            employee.permanent_address_id = None

        existing_social_link = {
            str(social_link.id): social_link
            for social_link in db.query(Models.SocialLinks)
            .filter(Models.SocialLinks.user_id == employee.id)
            .all()
        }

        social_links_to_update = []
        social_links_to_add = []

        for link in data.social_link:
            if link.id and str(link.id) in existing_social_link:
                social_links_to_update.append(link)
            else:
                social_links_to_add.append(link)

        if social_links_to_update:
            db.bulk_update_mappings(
                Models.SocialLinks,
                [
                    {**link.dict(exclude={"user_id", "id"}), "id": link.id}
                    for link in social_links_to_update
                ],
            )
        if social_links_to_add:
            db.bulk_insert_mappings(
                Models.SocialLinks,
                [
                    {
                        **link.dict(exclude={"user_id", "id"}),
                        "user_id": employee.id,
                    }
                    for link in social_links_to_add
                ],
            )
        db.commit()

        # Refresh the employee instance to get the latest data
        db.refresh(employee)

        return {
            "message": "User Info Updated Successfully",
            "success": True,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while Editing the User The User",
                "error": str(e),
                "success": False,
            },
        )


# * This Is An Api That Is Used To Fetch All The EmployeeOf The Given Organization
@employee_router.get("/fetch-all", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_all_employee(
    request: Request,
    db: db_dependencies,
    page: int = Query(..., alias="page"),
    limit: int = Query(..., alias="limit"),
    filter: Optional[str] = Query(None),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        filter_data = ""
        if filter:
            decoded = unquote(filter)
            filter_data = json.loads(decoded)

        query_data = db.query(Models.User).filter(
            Models.User.organization_id == user.organization_id
        )

        query_data = query_data.join(Models.User.personal_info)

        query_data = query_data.outerjoin(Models.User.employee_info)

        if filter_data:
            query_data = apply_query_filter(query_data, filter_data)

        total_data = query_data.count()
        page = page if page else 1
        limit = limit if limit else 10
        start = (page - 1) * limit
        end = start + limit
        query_data = query_data.offset(start).limit(end)

        query_data = query_data.options(
            joinedload(Models.User.personal_info),
            joinedload(Models.User.employee_info)
            .joinedload(Models.EmployeeInfo.reporting_manager)
            .joinedload(Models.User.personal_info),
            joinedload(Models.User.employee_info)
            .joinedload(Models.EmployeeInfo.reporting_manager)
            .joinedload(Models.User.employee_info),
            joinedload(Models.User.employee_info).joinedload(Models.EmployeeInfo.employee_role),
        )

        employee_data = query_data.all()

        _data = []

        for employee in employee_data:
            employee_dict = filter_fields(employee, fields=["account_status", "organization_id"])
            personal_info = filter_fields(employee.personal_info) if employee.personal_info else {}
            employee_info = {}
            reporting_manager_info = {}

            if employee.employee_info:
                employee_info = filter_fields(employee.employee_info, fields=["-reporting_manager"])

                if employee.employee_info.reporting_manager:

                    reporting_manager_info = {
                        **filter_fields(employee.employee_info.reporting_manager, fields=["id"]),
                    }
                    if employee.employee_info.reporting_manager.personal_info:
                        reporting_manager_info.update(
                            filter_fields(
                                employee.employee_info.reporting_manager.personal_info,
                                fields=[
                                    "id",
                                    "first_name",
                                    "last_name",
                                    "middle_name",
                                    "profile_picture",
                                    "profile_picture_bg",
                                    "full_name",
                                    "gender",
                                ],
                            )
                        )
                    if employee.employee_info.reporting_manager.employee_info:
                        reporting_manager_info.update(
                            filter_fields(
                                employee.employee_info.reporting_manager.employee_info,
                                fields=["employee_code"],
                            )
                        )

            _data.append(
                {
                    **employee_dict,
                    "personal_info": personal_info,
                    "employee_info": {
                        **employee_info,
                        "reporting_manager": (
                            reporting_manager_info if reporting_manager_info else None
                        ),
                    },
                }
            )

        return {
            "message": "user verified successfully",
            "success": True,
            "data": _data,
            "filter_data": filter_data,
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
                "message": "error while Fetching All The Employee",
                "error": str(e),
                "success": False,
            },
        )


@employee_router.get("/fetch-employee", status_code=status.HTTP_200_OK)
async def Fetch_Employee(
    request: Request,
    db: db_dependencies,
    query: str = Query(..., description="name Of The Person"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        query_data = db.query(Models.User).filter(
            Models.User.organization_id == user.organization_id
        )

        query_data = query_data.join(Models.User.personal_info)

        query_data = query_data.filter(
            Models.PersonalInfo.normalized_full_name.ilike(f"%{query.lower().replace(' ', '')}%")
        )

        query_data = query_data.options(
            joinedload(Models.User.personal_info),
        )

        employee_data = query_data.all()

        _data = []

        for employee in employee_data:
            employee_dict = filter_fields(employee, fields=["account_status", "organization_id"])
            personal_info = filter_fields(employee.personal_info) if employee.personal_info else {}
            employee_info = (
                filter_fields(employee.employee_info, fields=["-reporting_manager"])
                if employee.employee_info
                else {}
            )

            _data.append(
                {
                    "id": employee.id,
                    **employee_dict,
                    **filter_fields(
                        personal_info,
                        fields=["first_name", "full_name", "middle_name", "last_name"],
                    ),
                    **filter_fields(employee_info, fields=["employee_code"]),
                }
            )

        return {
            "message": "Employee Fetched Successfully",
            "success": True,
            "data": _data,
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while Fetching All The Employee",
                "error": str(e),
                "success": False,
            },
        )
