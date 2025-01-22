from fastapi import APIRouter, Depends, HTTPException, status
from SqlModels import Models
from Database.Database import db_dependencies
from Helper.jwtHelper import create_jwt_token, hash_passwords, verify_password
from Helper.helper import generate_full_name, filter_fields
from PydenticModels.UserModels import LoginUserInfo, SignUpUserInfo, User
from Middelware.verifyToken import oauth2_scheme, verify_token


authRoutes = APIRouter(prefix="/app/v1/auth", tags=["auth"])



@authRoutes.post(path="/signUp", status_code=status.HTTP_201_CREATED)
async def sign_up(db: db_dependencies, user_info: User):
    try:
        hashed_password = hash_passwords("lndnnlwfnwnwnqfnwl")
        print(user_info)

        # Create the related models first
        personal_info = Models.PersonalInfo(
            first_name=user_info.personal_info.first_name,
            last_name=user_info.personal_info.last_name,
            middle_name=user_info.personal_info.middle_name,
            gender=user_info.personal_info.gender,
            date_of_birth=user_info.personal_info.date_of_birth,
        )

        employee_info = Models.EmployeeInfo(
            employee_email=user_info.employee_info.employee_email,
            organization_name=user_info.employee_info.organization_name,
            department=user_info.employee_info.department,
            designation=user_info.employee_info.designation,
            employee_code=user_info.employee_info.employee_code,
            reporting_to_id=user_info.employee_info.reporting_to_id,
        )

        # Handling children: Creating a list of `Children` model instances
        children = [
            Models.Children(
                name=child.name, gender=child.gender, date_of_birth=child.date_of_birth
            )
            for child in user_info.family_info.children
        ]

        family_info = Models.FamilyInfo(
            marital_status=user_info.family_info.marital_status,
            children=children,  # List of `Children` model instances
        )

        address = Models.Address(
            address=user_info.address.address,
            city=user_info.address.city,
            state=user_info.address.state,
            country=user_info.address.country,
            zip_code=user_info.address.zip_code,
        )

        emergency_contact = [
            Models.EmergencyContact(
                full_name=contact.full_name, contact_number=contact.contact_number
            )
            for contact in user_info.emergency_contact
        ]

        social_links = {"icon": "rew", "name": "rew", "link": "rew"}

        # Create the User instance
        new_user = Models.User(
            password=hashed_password,
            social_link=social_links,
        )

        print(new_user)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user = {
            "id": new_user.id,
            "personal_info": {
                "first_name": personal_info.first_name,
                "last_name": personal_info.last_name,
                "middle_name": personal_info.middle_name,
                "gender": personal_info.gender,
                "date_of_birth": personal_info.date_of_birth,
            },
            "employee_info": {
                "employee_email": employee_info.employee_email,
                "organization_name": employee_info.organization_name,
                "department": employee_info.department,
                "designation": employee_info.designation,
                "employee_code": employee_info.employee_code,
                "reporting_to_id": employee_info.reporting_to_id,
            },
            "children": [
                {
                    "name": child.name,
                    "gender": child.gender,
                    "date_of_birth": child.date_of_birth,
                }
                for child in children
            ],
            "address": {
                "address": address.address,
                "city": address.city,
                "state": address.state,
                "country": address.country,
                "zip_code": address.zip_code,
            },
            "emergency_contact": [
                {
                    "full_name": contact.full_name,
                    "contact_number": contact.contact_number,
                }
                for contact in emergency_contact
            ],
        }

        # JWT token creation
        token_data = {"sub": new_user.id}
        token = create_jwt_token(data=token_data)

        return {
            "message": "The User Is Registered Successfully",
            "token": token,
            "success": True,
            "user_info": user,
        }

    except HTTPException:
        raise

    except Exception as e:
        # Log the error here if you have logging set up
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the user",
        )
