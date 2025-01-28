from fastapi import APIRouter, Depends, HTTPException, status
from SqlModels import Models
from Database.Database import db_dependencies
from Helper.jwtHelper import create_jwt_token, hash_passwords, verify_password
from Helper.helper import generate_full_name, model_to_filtered_dict
from PydanticModels.UserModels import User
from Helper.createModelInstance import cerate_model_instance


authRoutes = APIRouter(prefix="/app/v1/auth", tags=["auth"])


@authRoutes.post(path="/add-employee", status_code=status.HTTP_201_CREATED)
async def add_employee(db: db_dependencies, user: User):
    try:
        find_user = (
            db.query(Models.EmployeeInfo)
            .filter(
                Models.EmployeeInfo.employee_email == user.employee_info.employee_email
            )
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

        personal_info = cerate_model_instance(
            model=Models.PersonalInfo, data=user.personal_info
        )
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

        address_info = cerate_model_instance(
            model=Models.Address, data=user.address, fields=[]
        )
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
            {"icon": item.icon, "name": item.name, "link": item.link}
            for item in social_link
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
