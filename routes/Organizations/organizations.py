from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Query
from PydanticModels.Organizations.organizations import RegisterOrganizationInfo
from Database.Database import db_dependencies
from SqlModels import Models
from Helper.createModelInstance import cerate_model_instance
from Helper.emailSender import email_sender_function, EmailSchema
from Helper.upsert_record import upsert_record
from PydanticModels.Organizations.organizations import OnboardingOrganization
from sqlalchemy.sql import func
from Helper.helper import (
    model_to_filtered_dict,
    urlsafe_data_encoding_function,
    urlsafe_data_decoding_function,
)
import json


orgRouter = APIRouter(prefix="/app/v1/organization", tags=["organization"])


@orgRouter.post("/sign-up", status_code=status.HTTP_201_CREATED)
async def create_organization(
    organization_info: RegisterOrganizationInfo,
    db: db_dependencies,
    background_task: BackgroundTasks,
):
    try:
        print(organization_info.primary_email.split("@"))
        find_organization = (
            db.query(Models.OrganizationGeneralInfo)
            .filter(
                Models.OrganizationGeneralInfo.primary_email
                == organization_info.primary_email
            )
            .first()
        )
        check_for_the_email_domain = (
            db.query(Models.OrganizationGeneralInfo)
            .filter(
                func.substring_index(
                    Models.OrganizationGeneralInfo.primary_email, "@", -1
                )
                == organization_info.primary_email.split("@")[1]
            )
            .first()
        )

        if check_for_the_email_domain:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "The Provided Email Domain Is Already In Use",
                    "success": False,
                    "email": find_organization.primary_email,
                },
            )

        if find_organization:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "The Provided Email Is Already In Use",
                    "success": False,
                    "email": find_organization.primary_email,
                },
            )

        create_org = Models.Organization(status=True)

        db.add(create_org)
        db.commit()
        db.refresh(create_org)

        organization = cerate_model_instance(
            model=Models.OrganizationGeneralInfo,
            data=organization_info,
            fields=["-country_info"],
        )
        user_info = Models.User(password="")
        user_info.organization_id = create_org.id
        db.add(user_info)
        db.commit()
        db.refresh(user_info)
        user_employee_info = Models.EmployeeInfo(
            status="Active",
            organization_name=organization_info.organization_name,
            employee_code="",
            department="",
            designation="",
            reporting_to={},
            employee_role="",
            employee_email=organization_info.primary_email,
        )
        user_employee_info.user_id = user_info.id
        db.add(user_employee_info)
        db.commit()
        db.refresh(user_employee_info)
        organization.organization_id = create_org.id

        organization.country_info = json.dumps(
            organization_info.country_info.dict()
            if hasattr(organization_info.country_info, "dict")
            else organization_info.country_info
        )

        db.add(organization)
        db.commit()
        db.refresh(organization)

        encrypted_org_id = urlsafe_data_encoding_function(create_org.id)

        email_data = {
            "recever_email": organization_info.primary_email,
            "subject": "hello from the test mail",
            "body": f"http://127.0.0.1:8000/app/v1/organization/verify-organization?organization-id={encrypted_org_id}",
        }

        email_instance = EmailSchema(**email_data)

        send_mail = email_sender_function(email_instance, background_task)

        return {
            "organization": organization,
            "email_status": send_mail,
            "encrypted_url": f"http://127.0.0.1:8000/app/v1/organization/verify-organization?organization-id={encrypted_org_id}",
            "employee_info": model_to_filtered_dict(user_employee_info),
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


@orgRouter.post("/verify-organization", status_code=status.HTTP_200_OK)
async def verify_organization(
    db: db_dependencies,
    organization_id: str = Query(..., alias="organization-id"),
):
    try:
        decrypted_data = urlsafe_data_decoding_function(organization_id)

        organization = (
            db.query(Models.OrganizationGeneralInfo)
            .filter(Models.OrganizationGeneralInfo.organization_id == decrypted_data)
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
                .filter(
                    Models.EmployeeInfo.employee_email == organization.primary_email
                )
                .first()
            )

            encrypted_user_id = urlsafe_data_encoding_function(user_info.user_id)

            return {
                "message": "Organization Is Verified Successfully",
                "data": model_to_filtered_dict(organization),
                "success": True,
                "alreadyVerified": False,
                "user_info": model_to_filtered_dict(user_info),
            }
        else:
            user_info = (
                db.query(Models.EmployeeInfo)
                .filter(
                    Models.EmployeeInfo.employee_email == organization.primary_email
                )
                .first()
            )

            encrypted_user_id = urlsafe_data_encoding_function(user_info.user_id)

            return {
                "message": "Organization already Verified",
                "data": model_to_filtered_dict(organization),
                "success": True,
                "alreadyVerified": True,
                "encrypted_user_id": encrypted_user_id,
                "user_info": model_to_filtered_dict(user_info),
                "encrypted_url": f"http://127.0.0.1:8000/app/v1/auth/create-password?user-id={encrypted_user_id}",
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


# todo working on this api
# @orgRouter.post("/onboard-organization", status_code=status.HTTP_200_OK)
# async def onboard_organization(
#     db: db_dependencies,
#     data: OnboardingOrganization,
#     organization_id: str = Query(..., alias="organization-id"),
# ):
#     try:
#         # first we will create the new model

#         for each_address in data.address:
#             organization_address = cerate_model_instance(
#                 model=Models.OrganizationAddress, data=each_address
#             )
#             organization_address.organization_id = organization_id
#             db.add(organization_address)
#             db.commit()
#             db.refresh(organization_address)

#         for each_contact in data.contact_info:
#             contact_info = cerate_model_instance(
#                 model=Models.OrganizationContactInfo, data=each_contact
#             )
#             db.add(contact_info)
#             db.commit()
#             db.refresh(contact_info)
#         for about    

#     except HTTPException as http_exception:
#         raise http_exception
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail={
#                 "message": "error while onboarding the organization",
#                 "error": str(e),
#             },
#         )
