from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Query
from PydanticModels.Organizations.organizations import RegisterOrganizationInfo
from Database.Database import db_dependencies
from SqlModels import Models
from Helper.createModelInstance import cerate_model_instance
from Helper.emailSender import email_sender_function, EmailSchema
from PydanticModels.Organizations.organizations import OnboardingOrganization
from sqlalchemy.sql import func
from Helper.helper import (
    model_to_filtered_dict,
    urlsafe_data_encoding_function,
    urlsafe_data_decoding_function,
    update_model_data,
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
                    "owner_email": find_organization.primary_email,
                    "tttsss": check_for_the_email_domain.organization_id,
                },
            )

        if find_organization:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "The Provided Email Is Already In Use",
                    "success": False,
                    "owner_email": find_organization.primary_email,
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
            "message": "organization Created SuccessFully",
            "email_status": send_mail,
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


@orgRouter.get("/verify-organization", status_code=status.HTTP_200_OK)
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
                "success": True,
                "alreadyVerified": False,
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
            # todo need to add email
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
@orgRouter.post("/onboard-organization", status_code=status.HTTP_200_OK)
async def onboard_organization(
    db: db_dependencies,
    data: OnboardingOrganization,
    organization_id: str = Query(..., alias="organization-id"),
):
    try:

        organization = (
            db.query(Models.Organization)
            .filter(Models.Organization.id == organization_id)
            .first()
        )
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Organization Not Found",
                    "success": False,
                },
            )
        updated_general_info = update_model_data(
            db=db,
            model=Models.OrganizationGeneralInfo,
            model_id=organization_id,
            id_field="organization_id",
            updated_data=data.general_info,
        )

        address_arr = []
        for each_address in data.address:
            address = cerate_model_instance(
                model=Models.OrganizationAddress, data=each_address
            )
            address.organization_id = organization.id
            db.add(address)
            db.commit()

            address_arr.append(address)

        contact_info_arr = []

        for each_contact in data.contact_info:
            contact = cerate_model_instance(
                data=each_contact, model=Models.OrganizationContactInfo
            )
            contact.organization_id = organization.id
            db.add(contact)
            db.commit()

            contact_info_arr.append(contact)

        about_info = cerate_model_instance(
            model=Models.OrganizationAboutInfo, data=data.about_info
        )
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
                "general_info": model_to_filtered_dict(updated_general_info),
                "address": [
                    model_to_filtered_dict(_address) for _address in address_arr
                ],
                "contact_info": [
                    model_to_filtered_dict(_contact_info)
                    for _contact_info in contact_info_arr
                ],
                "about_info": model_to_filtered_dict(about_info),
                "organization_settings": model_to_filtered_dict(organization_settings),
            },
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
