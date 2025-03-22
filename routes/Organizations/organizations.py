import json
import os

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy.sql import func

from Database.Database import db_dependencies
from Helper.createModelInstance import cerate_model_instance
from Helper.emailSender import EmailSchema, email_sender_function
from Helper.helper import (
    model_to_filtered_dict,
    update_model_data,
    urlsafe_data_decoding_function,
    urlsafe_data_encoding_function,
)
from Email.VerifyEmailHtmlBody import VerifyEmailHtmlBody
from PydanticModels.Organizations.organizations import (
    OnboardingOrganization,
    RegisterOrganizationInfo,
    VerifyMetaTag,
)
from SqlModels import Models

load_dotenv(override=True)

orgRouter = APIRouter(prefix="/app/v1/organization", tags=["organization"])


FRONTEND_URL = os.getenv("FRONTEND_URL").encode()


@orgRouter.post("/sign-up", status_code=status.HTTP_201_CREATED)
async def create_organization(
    organization_info: RegisterOrganizationInfo,
    db: db_dependencies,
    background_task: BackgroundTasks,
):
    try:
        find_organization = (
            db.query(Models.OrganizationGeneralInfo)
            .filter(Models.OrganizationGeneralInfo.primary_email == organization_info.primary_email)
            .first()
        )
        check_for_the_email_domain = (
            db.query(Models.OrganizationGeneralInfo)
            .filter(
                func.substring_index(Models.OrganizationGeneralInfo.primary_email, "@", -1)
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

        config_module = Models.ConfigModule()
        config_module.organization_id = create_org.id
        db.add(config_module)
        db.commit()
        db.refresh(config_module)

        encrypted_org_id = urlsafe_data_encoding_function(create_org.id)

        email_data = {
            "recever_email": organization_info.primary_email,
            "subject": "hello from the test mail",
            "body": VerifyEmailHtmlBody(
                f"{FRONTEND_URL}/verification/verify-email?organization-id={encrypted_org_id}"
            ),
        }

        email_instance = EmailSchema(**email_data)

        send_mail = email_sender_function(email_instance, background_task)

        return {
            "success": True,
            "title": "Organization Created",
            "message": f"Your organization has been successfully created. A confirmation email with further details has been sent to {user_employee_info.employee_email}. Please check your inbox and follow the instructions to complete the setup.",
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


@orgRouter.post("/verify-meta-tag", status_code=status.HTTP_200_OK)
async def verify_meta_tag(data: VerifyMetaTag):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(data.website_url)
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        meta_tag = soup.find("meta", attrs={"name": data.meta_name})

        if not meta_tag:
            return {
                "meta_found": False,
                "expected_value": data.meta_value,
                "actual_value": "",
                "match": False,
                "success": False,
            }

        if meta_tag and "content" in meta_tag.attrs:
            actual_value = meta_tag.get("content", "")

            verified = actual_value == data.meta_value

            return {
                "meta_found": True,
                "expected_value": data.meta_value,
                "actual_value": actual_value,
                "match": verified,
                "success": True,
            }
        return {"error": "Meta tag not found"}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error Accrued While Verifying The Meta Tag",
                "success": False,
                "error": str(e),
            },
        )


@orgRouter.get("/verify-organization", status_code=status.HTTP_200_OK)
async def verify_organization(
    db: db_dependencies,
    background_task: BackgroundTasks,
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
                .filter(Models.EmployeeInfo.employee_email == organization.primary_email)
                .first()
            )

            encrypted_user_id = urlsafe_data_encoding_function(user_info.user_id)

            email_data = {
                "recever_email": user_info.employee_email,
                "subject": "hello from the test mail",
                "body": VerifyEmailHtmlBody(
                    f"{FRONTEND_URL}/auth/create-password?user-id={encrypted_user_id}"
                ),
            }

            email_instance = EmailSchema(**email_data)

            email_sender_function(email_instance, background_task)

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


@orgRouter.post("/onboard-organization", status_code=status.HTTP_200_OK)
async def onboard_organization(
    db: db_dependencies,
    data: OnboardingOrganization,
    organization_id: str = Query(..., alias="organization-id"),
):
    try:
        organization_id = urlsafe_data_decoding_function(organization_id)
        print(organization_id)
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
