from fastapi import APIRouter, HTTPException, status
from PydanticModels.Organizations.organizations import RegisterOrganizationInfo
from Database.Database import db_dependencies
from SqlModels import Models
from Helper.createModelInstance import cerate_model_instance
import json

orgRouter = APIRouter(prefix="/app/v1/organization", tags=["organization"])


@orgRouter.post("/register-organization", status_code=status.HTTP_201_CREATED)
async def create_organization(
    organization_info: RegisterOrganizationInfo, db: db_dependencies
):
    try:
        find_organization = (
            db.query(Models.OrganizationGeneralInfo)
            .filter(
                Models.OrganizationGeneralInfo.primary_email
                == organization_info.primary_email
            )
            .first()
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
        organization.organization_id = create_org.id
        organization.country_info = json.dumps(
            organization_info.country_info.dict()
            if hasattr(organization_info.country_info, "dict")
            else organization_info.country_info
        )

        db.add(organization)
        db.commit()
        db.refresh(organization)
        return organization
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
