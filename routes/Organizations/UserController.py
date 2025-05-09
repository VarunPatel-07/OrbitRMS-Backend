import os

from dotenv import load_dotenv
from fastapi import APIRouter, status, Depends, HTTPException, Query
from Database.Database import db_dependencies
from Middleware.verifyToken import verify_token
from PydanticModels.Organizations.AddEditEmployeePydanticModal import AddEditUserProfileModel
from SqlModels import Models
from Helper.createModelInstance import cerate_model_instance
from Helper.jwtHelper import hash_passwords
from Helper.helper import (
    model_to_filtered_dict,
    urlsafe_data_decoding_function,
    urlsafe_data_encoding_function,
)

load_dotenv(override=True)

SUPER_SECURE_HASH_PASSWORD = os.getenv("SUPER_SECURE_HASH_PASSWORD", "").strip()

userRoute = APIRouter(prefix="/app/v1/user-controller", tags=["user-controller"])


@userRoute.post("/add", status_code=status.HTTP_200_OK)
async def handel_add_user_function(
    db: db_dependencies,
    data: AddEditUserProfileModel,
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
