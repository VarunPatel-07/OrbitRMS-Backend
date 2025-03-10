from fastapi import APIRouter, Depends, HTTPException, Query, status

from Database.Database import db_dependencies
from Helper.createModelInstance import cerate_model_instance
from Helper.helper import (
    model_to_filtered_dict,
    urlsafe_data_decoding_function,
    urlsafe_data_encoding_function,
)
from Helper.jwtHelper import create_jwt_token, hash_passwords, verify_password
from Middleware.verifyToken import verify_token
from PydanticModels.authentication.AuthenticationModels import CreatePassword, SignIn
from PydanticModels.UserModels import User
from SqlModels import Models

authRoutes = APIRouter(prefix="/app/v1/auth", tags=["auth"])


@authRoutes.post(path="/add-employee", status_code=status.HTTP_201_CREATED)
async def add_employee(db: db_dependencies, user: User):
    try:
        find_user = (
            db.query(Models.EmployeeInfo)
            .filter(Models.EmployeeInfo.employee_email == user.employee_info.employee_email)
            .first()
        )

        if find_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "User With This Mail Already Exists",
                    "success": False,
                },
            )

        hashed_password = hash_passwords("Orbit@1234")

        created_user = Models.User(password=hashed_password)
        db.add(created_user)
        db.commit()

        personal_info = cerate_model_instance(model=Models.PersonalInfo, data=user.personal_info)
        personal_info.user_id = created_user.id

        employee_info = cerate_model_instance(
            model=Models.EmployeeInfo,
            data=user.employee_info,
        )
        employee_info.user_id = created_user.id

        personal_contact_info = cerate_model_instance(
            model=Models.PersonalContactInfo,
            data=user.personal_contact_info,
        )
        personal_contact_info.user_id = created_user.id

        family_info = None

        children_arr = []
        if user.family_info.children:
            family_info = Models.FamilyInfo(
                father_name=user.family_info.father_name,
                mother_name=user.family_info.mother_name,
                marital_status=user.family_info.marital_status,
                children=children_arr,  # Initial empty children list
            )
            family_info.user_id = created_user.id

            db.add(family_info)
            db.commit()
            children_arr = [
                Models.Children(
                    name=child.name,
                    gender=child.gender,
                    date_of_birth=child.date_of_birth,
                    family_id=family_info.id,  # Set the family_id for each child
                )
                for child in user.family_info.children
            ]
        else:
            family_info = Models.FamilyInfo(
                father_name=user.family_info.father_name,
                mother_name=user.family_info.mother_name,
                marital_status=user.family_info.marital_status,
                children=children_arr,  # Initial empty children list
            )
            family_info.user_id = created_user.id

            db.add(family_info)
            db.commit()

        address_info = cerate_model_instance(model=Models.Address, data=user.address, fields=[])
        address_info.user_id = created_user.id

        emergency_contact = [
            Models.EmergencyContact(
                full_name=contact.full_name,
                contact_number=contact.contact_number,
                user_id=created_user.id,
            )
            for contact in user.emergency_contact
        ]

        social_link = [
            Models.SocialLinks(
                icon=link.icon, name=link.name, link=link.link, user_id=created_user.id
            )
            for link in user.social_link
        ]

        children = []
        if user.family_info.children:
            children = [
                {
                    "name": child.name,
                    "gender": child.gender,
                    "date_of_birth": child.date_of_birth,
                }
                for child in children_arr
            ]

        emergency_contacts = [
            {"full_name": item.full_name, "contact_number": item.contact_number}
            for item in emergency_contact
        ]
        social_links = [
            {"icon": item.icon, "name": item.name, "link": item.link} for item in social_link
        ]

        db.add(employee_info)
        db.add(personal_info)
        db.add(personal_contact_info)
        db.add(address_info)
        for child in children_arr:
            db.add()(child)
        for contact in emergency_contact:
            db.add(contact)
        for link in social_link:
            db.add(link)
        db.commit()

        user_info = {
            "password": created_user.password,
            "personal_info": model_to_filtered_dict(personal_info),
            "employee_info": model_to_filtered_dict(employee_info),
            "personal_contact_info": model_to_filtered_dict(personal_contact_info),
            "family_info": {
                "father_name": family_info.father_name,
                "mother_name": family_info.mother_name,
                "marital_status": family_info.marital_status,
                "children": children,
            },
            "address_info": model_to_filtered_dict(address_info),
            "emergency_contact": emergency_contacts,
            "social_link": social_links,
        }

        # JWT token creation
        token_data = {"sub": created_user.id}
        token = create_jwt_token(data=token_data)

        return {
            "message": "The User Is Registered Successfully",
            "token": token,
            "success": True,
            "user_info": user_info,
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


@authRoutes.post(path="/create-password", status_code=status.HTTP_201_CREATED)
async def create_password(
    db: db_dependencies,
    password: CreatePassword,
    user_id: str = Query(..., alias="user-id"),
):
    try:
        decrypted_user_id = urlsafe_data_decoding_function(user_id)

        user = db.query(Models.User).filter(Models.User.id == decrypted_user_id).first()

        hash_password = hash_passwords(password.password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "user not found", "success": False},
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


@authRoutes.post(path="/sign-in", status_code=status.HTTP_200_OK)
async def sing_in(db: db_dependencies, user_info: SignIn):
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

        check_password = verify_password(
            plain_password=user_info.password, hashed_password=user.password
        )

        if not check_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid Email Or Password", "success": False},
            )
        sub = {"user_id": user.id}
        token = create_jwt_token(data=sub)

        encrypted_org_id = urlsafe_data_encoding_function(organization.id)

        return {
            "message": "User Sign In Successfully",
            "success": True,
            "authenticationToken": token,
            "organization_created": organization.organization_created,
            "organization_id": encrypted_org_id,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error accrued while signing in",
                "success": False,
            },
        )


@authRoutes.get(path="/verify-user", status_code=status.HTTP_200_OK)
async def verify_user(db: db_dependencies, token: str = Depends(verify_token)):
    try:
        user_id = token["user_id"]

        user = db.query(Models.User).filter(Models.User.id == user_id).first()

        employee_info = (
            db.query(Models.EmployeeInfo).filter(Models.EmployeeInfo.user_id == user_id).first()
        )
        organization = (
            db.query(Models.Organization)
            .filter(Models.Organization.id == user.organization_id)
            .first()
        )
        organization_general_info = (
            db.query(Models.OrganizationGeneralInfo)
            .filter(Models.OrganizationGeneralInfo.organization_id == user.organization_id)
            .first()
        )
        organization_address = (
            db.query(Models.OrganizationAddress)
            .filter(Models.OrganizationAddress.organization_id == user.organization_id)
            .first()
        )

        organization_contact_info = (
            db.query(Models.OrganizationContactInfo)
            .filter(Models.OrganizationContactInfo.organization_id == user.organization_id)
            .first()
        )

        organization_about_info = (
            db.query(Models.OrganizationAboutInfo)
            .filter(Models.OrganizationAboutInfo.organization_id == user.organization_id)
            .first()
        )

        organization_settings = (
            db.query(Models.OrganizationSettings)
            .filter(Models.OrganizationSettings.organization_id == user.organization_id)
            .first()
        )
        return {
            "message": "user verified successfully",
            "success": True,
            "data": {
                "user": {
                    "employee_info": model_to_filtered_dict(employee_info),
                },
                "organization": {
                    "id": organization.id,
                    "general_info": model_to_filtered_dict(organization_general_info),
                    "address": model_to_filtered_dict(organization_address),
                    "contact_info": model_to_filtered_dict(organization_contact_info),
                    "about_info": model_to_filtered_dict(organization_about_info),
                    "organization_settings": model_to_filtered_dict(organization_settings),
                    "status": organization.status,
                    "organization_created": organization.organization_created,
                    "created_at": organization.created_at,
                    "updated_at": organization.updated_at,
                },
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while verifying user",
                "success": False,
                "error": str(e),
            },
        )
