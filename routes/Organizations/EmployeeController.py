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
from sqlalchemy.sql import func

from Database.Database import db_dependencies
from Email.HtmlEmailBody import WelcomeMailForNewlyAddedEmployee
from Helper.createModelInstance import cerate_model_instance
from Helper.emailSender import EmailSchema, email_sender_function
from Helper.helper import (
    filter_fields,
    update_model_data,
    urlsafe_data_encoding_function,
)
from Helper.jwtHelper import hash_passwords
from Middleware.verifyToken import verify_token
from PydanticModels.HelperPydanticModel import WelcomeEmployeeMailModel
from PydanticModels.Organizations.AddEditEmployeePydanticModal import (
    AddEditUserProfileModel,
)
from RateLimiting import limiter
from SqlModels import Models

from .EmployeeQueryFilters import apply_query_filter

load_dotenv(override=True)

SUPER_SECURE_HASH_PASSWORD = os.getenv("SUPER_SECURE_HASH_PASSWORD", "").strip()

FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip()

API_RATE_LIMITING = os.getenv("API_RATE_LIMITING")


alignable_for_child_info = [
    "Married",
    "Divorced",
    "Widowed",
    "Prefer not to say",
]

employee_router = APIRouter(prefix="/app/v1/employee", tags=["employee"])


@employee_router.post("/add", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def handel_add_user_function(
    request: Request,
    db: db_dependencies,
    data: AddEditUserProfileModel,
    background_task: BackgroundTasks,
    token: str = Depends(verify_token),
    organization_id: str = Query(..., alias="organization-id"),
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

        organization_info = (
            db.query(Models.Organization)
            .options(
                joinedload(Models.Organization.employees).joinedload(Models.User.personal_info),
                joinedload(Models.Organization.employees).joinedload(Models.User.employee_info),
            )
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

        def normalize_name(name: str) -> str:
            return " ".join(name.strip().split()).lower()

        existing_user = next(
            (
                employee
                for employee in organization_info.employees
                if employee.personal_info
                and normalize_name(employee.personal_info.full_name)
                == normalize_name(data.personal_info.full_name)
            ),
            None,
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Employee With This Name Already Exist",
                    "success": False,
                },
            )

        user_with_same_email = next(
            (
                employee
                for employee in organization_info.employees
                if employee.employee_info
                and employee.employee_info.employee_email == data.employee_info.employee_email
            ),
            None,
        )

        if user_with_same_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "The Employee With This Mail Already Exist", "success": False},
            )

        user_with_same_employee_code = next(
            (
                employee
                for employee in organization_info.employees
                if employee.employee_info
                and employee.employee_info.employee_code == data.employee_info.employee_code
            ),
            None,
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
        db.commit()
        db.refresh(personal_contact_info)

        emergency_contact_array = []
        for emergency_contact in data.personal_contact_info.emergency_contacts:
            contact = cerate_model_instance(
                model=Models.EmergencyContact, data=emergency_contact, fields=["-contact_id", "-id"]
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
        for link in data.social_link:
            if link.name and link.link and link.icon:
                social_link = cerate_model_instance(
                    model=Models.SocialLinks, data=link, fields=["-user_id", "-id"]
                )
                social_link.user_id = new_user.id
                social_links_array.append(social_link)
        if social_links_array:
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
@limiter.limit(API_RATE_LIMITING)
async def handel_fetch_profile_info(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    employee_id: str = Query(..., alias="employee_id"),
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

        return {
            "message": "user verified successfully",
            "success": True,
            "data": {
                **filter_fields(
                    employee_data,
                    fields=[
                        "-password",
                        "-personal_info",
                        "-personal_contact_info",
                        "-family_info",
                        "-employee_info",
                    ],
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
                    else {}
                ),
                "personal_contact_info": (
                    filter_fields(employee_data.personal_contact_info[0])
                    if employee_data.personal_contact_info
                    else {}
                ),
                "family_info": (
                    filter_fields(employee_data.family_info[0]) if employee_data.family_info else {}
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
    token: str = Depends(verify_token),
    employee_id: str = Query(..., alias="employee-id"),
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

        employee = db.query(Models.User).filter(Models.User.id == employee_id).first()
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

        personal_info = update_model_data(
            db=db,
            model=Models.PersonalInfo,
            model_id=employee.id,
            id_field="user_id",
            updated_data=data.personal_info,
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

        employee_info = (
            db.query(Models.EmployeeInfo).filter(Models.EmployeeInfo.user_id == employee.id).first()
        )
        employee_info.status = data.employee_info.status
        employee_info.employee_type = data.employee_info.employee_type
        employee_info.organization_name = data.employee_info.organization_name
        employee_info.employee_code = data.employee_info.employee_code
        employee_info.department = data.employee_info.department
        employee_info.designation = data.employee_info.designation
        employee_info.employee_email = data.employee_info.employee_email
        employee_info.joining_date = data.employee_info.joining_date
        employee_info.employee_role_id = data.employee_info.employee_role.role_id
        employee_info.reporting_to_id = data.employee_info.reporting_to.id

        db.commit()
        db.refresh(employee_info)

        personal_contact_info_data = data.personal_contact_info.dict(exclude={"emergency_contacts"})

        find_personal_contact_info = (
            db.query(Models.PersonalContactInfo)
            .filter(Models.PersonalContactInfo.user_id == employee.id)
            .first()
        )

        if find_personal_contact_info:
            personal_contact_info = update_model_data(
                db=db,
                model=Models.PersonalContactInfo,
                model_id=employee.id,
                id_field="user_id",
                updated_data=personal_contact_info_data,
                filter_fields=["-emergency_contacts"],
            )

        else:
            personal_contact_info = cerate_model_instance(
                model=Models.PersonalContactInfo,
                data=personal_contact_info_data,
                fields=["-user_id"],
            )
            personal_contact_info.user_id = employee.id
            db.add(personal_contact_info)
            db.commit()
            db.refresh(personal_contact_info)

        existing_contacts = (
            db.query(Models.EmergencyContact)
            .filter(Models.EmergencyContact.contact_id == personal_contact_info.id)
            .all()
        )
        existing_contacts_ids_map = [contact.id for contact in existing_contacts]

        new_contacts = []

        for emergency_contact in data.personal_contact_info.emergency_contacts:
            if emergency_contact.id in existing_contacts_ids_map:
                update_model_data(
                    db=db,
                    model=Models.EmergencyContact,
                    model_id=emergency_contact.id,
                    id_field="id",
                    updated_data=emergency_contact.dict(exclude={"contact_id", "id"}),
                    filter_fields=["-contact_id", "-id"],
                )
            else:

                contact = cerate_model_instance(
                    model=Models.EmergencyContact,
                    data=emergency_contact.dict(exclude={"contact_id", "id"}),
                    fields=["-contact_id", "-id"],
                )
                contact.contact_id = personal_contact_info.id
                new_contacts.append(contact)

        db.add_all(new_contacts)
        db.commit()

        find_family_info = (
            db.query(Models.FamilyInfo).filter(Models.FamilyInfo.user_id == employee.id).first()
        )
        family_info_data = data.family_info.dict(exclude={"children"})
        if find_family_info:
            family_info = update_model_data(
                db=db,
                model=Models.FamilyInfo,
                model_id=employee.id,
                id_field="user_id",
                updated_data=family_info_data,
            )
        else:
            family_info = cerate_model_instance(
                model=Models.FamilyInfo, data=family_info_data, fields=["-user_id"]
            )
            family_info.user_id = employee.id
            db.add(family_info)
            db.commit()
            db.refresh(family_info)

        if data.family_info.marital_status in alignable_for_child_info:

            existing_child = (
                db.query(Models.Children)
                .filter(Models.Children.family_info_id == find_family_info.id)
                .all()
            )

            existing_child_ids_map = [child.id for child in existing_child]
            print(existing_child_ids_map)

            children_array = []

            for each_child in data.family_info.children:
                if each_child.id in existing_child_ids_map:
                    update_model_data(
                        db=db,
                        model=Models.Children,
                        model_id=each_child.id,
                        id_field="id",
                        updated_data=each_child,
                        filter_fields=["-family_info_id", "-id"],
                    )
                else:
                    child = cerate_model_instance(
                        model=Models.Children, data=each_child, fields=["-family_info_id"]
                    )
                    child.family_info_id = family_info.id
                    children_array.append(child)
            db.add_all(children_array)
            db.commit()

        existing_current_address = (
            db.query(Models.Address)
            .filter(Models.Address.id == employee.current_address_id)
            .first()
        )

        employee.same_as_current_address = data.same_as_current_address

        if existing_current_address:
            update_model_data(
                db=db,
                model=Models.Address,
                model_id=employee.current_address_id,
                id_field="id",
                updated_data=data.current_address,
            )

        else:
            current_address = cerate_model_instance(model=Models.Address, data=data.current_address)
            db.add(current_address)
            db.commit()
            db.refresh(current_address)
            employee.current_address_id = current_address.id

        if not data.same_as_current_address:
            existing_permanent_address = (
                db.query(Models.Address)
                .filter(Models.Address.id == employee.permanent_address_id)
                .first()
            )
            if existing_permanent_address:
                update_model_data(
                    db=db,
                    model=Models.Address,
                    model_id=employee.permanent_address_id,
                    id_field="id",
                    updated_data=data.permanent_address,
                )
            else:
                permanent_address = cerate_model_instance(
                    model=Models.Address, data=data.permanent_address
                )
                db.add(permanent_address)
                db.commit()
                db.refresh(permanent_address)
                employee.permanent_address_id = permanent_address.id

        db.commit()
        db.refresh(employee)

        existing_social_link = (
            db.query(Models.SocialLinks).filter(Models.SocialLinks.user_id == employee.id).all()
        )

        existing_social_link_ids_map = [str(social_link.id) for social_link in existing_social_link]

        social_links_array = []
        for link in data.social_link:

            if link.id and str(link.id) in existing_social_link_ids_map:
                updated_link = (
                    db.query(Models.SocialLinks).filter(Models.SocialLinks.id == link.id).first()
                )
                updated_link.icon = link.icon
                updated_link.name = link.name
                updated_link.link = link.link
                updated_link.target_blank = link.target_blank

                db.commit()
                db.refresh(updated_link)
            else:
                if link.name and link.link and link.icon:
                    social_link = cerate_model_instance(
                        model=Models.SocialLinks,
                        data=link.dict(exclude={"user_id", "id"}),
                        fields=["-user_id", "-id"],
                    )
                    social_link.user_id = employee.id
                    social_links_array.append(social_link)

        if social_links_array:
            db.add_all(social_links_array)
        db.commit()

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
    token: str = Depends(verify_token),
    page: int = Query(..., alias="page"),
    limit: int = Query(..., alias="limit"),
    filter: Optional[str] = Query(None),
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
