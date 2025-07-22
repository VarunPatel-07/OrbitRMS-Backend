import os

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import joinedload
from Database.Database import db_dependencies
from Middleware.verifyToken import verify_token
from RateLimiting import limiter
from SqlModels import Models
from ErrorMessages.AuthErrorMessage import ADMIN_NOT_FOUND
from Helper.helper import model_to_filtered_dict, filter_fields

load_dotenv(override=True)

adminOrgRoute = APIRouter(prefix="/app/v1/admin/organization-manager", tags=["admin"])
API_RATE_LIMITING = os.getenv("API_RATE_LIMITING")


@adminOrgRoute.get(path="/fetch-organizations", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Fetch_All__Organization(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized", "success": False},
            )

        admin_id = token["admin_id"]
        session_id = token["session_id"]
        admin_signature = token["admin_signature"]

        admin = (
            db.query(Models.Admin)
            .options(joinedload(Models.Admin.admin_sessions))
            .filter(Models.Admin.id == admin_id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ADMIN_NOT_FOUND, "success": False},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid session", "success": False},
            )

        organizations = (
            db.query(Models.Organization)
            .options(
                joinedload(Models.Organization.general_info),
                joinedload(Models.Organization.address),
                joinedload(Models.Organization.contact_info),
                joinedload(Models.Organization.about_info),
                joinedload(Models.Organization.organization_settings),
            )
            .all()
        )

        return {
            "message": "Organizations fetched successfully",
            "success": True,
            "data": [
                {
                    **model_to_filtered_dict(org),
                    "primary_email": org.general_info.primary_email,
                    "primary_number": org.general_info.primary_number,
                    "organization_name": org.general_info.organization_name,
                    "organization_image": org.general_info.organization_profile_picture,
                    "email_domain_slug": org.organization_settings[0].email_domain_slug,
                    "is_meta_verified": org.general_info.is_meta_verified,
                    "email_verified": org.general_info.email_verified,
                    "employee_code_prefix": org.organization_settings[0].employee_code_prefix,
                    "intern_code_prefix": org.organization_settings[0].intern_code_prefix,
                    "country_info": org.general_info.country_info,
                    "organization_address": {
                        "country": org.address[0].country,
                        "country_code": org.address[0].country_code,
                    },
                }
                for org in organizations
            ],
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while Verifying Admin",
                "error": str(e),
                "success": False,
            },
        )
