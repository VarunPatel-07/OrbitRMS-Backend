import json
import math
import os
from typing import Optional
from urllib.parse import unquote

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import aliased, joinedload

from Config.EnvConfig import EnvConfig
from Database.Database import db_dependencies
from ErrorMessages.AuthErrorMessage import ADMIN_NOT_FOUND
from Helper.helper import filter_fields, model_to_filtered_dict
from Middleware.verifyToken import verify_token
from RateLimiting import limiter
from SqlModels import Models

from .OrganizationQueryFilters import Apply_Organization_Query_Filter

load_dotenv(override=True)

adminOrgRoute = APIRouter(prefix="/app/v1/admin/organization-manager", tags=["admin"])
API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING


@adminOrgRoute.get(path="/fetch-organizations", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Fetch_All__Organization(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    page: int = Query(..., alias="page"),
    limit: int = Query(..., alias="limit"),
    filter: Optional[str] = Query(None),
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

        filter_data: str = ""

        if filter:
            decoded = unquote(filter)
            filter_data = json.loads(decoded)

        org_query_data = db.query(Models.Organization)

        if org_query_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "No organizations found", "success": False},
            )

        org_query_data = org_query_data.outerjoin(Models.Organization.general_info)
        org_query_data = org_query_data.outerjoin(Models.Organization.address)

        if filter_data:
            org_query_data = Apply_Organization_Query_Filter(org_query_data, filter_data)

        total_data = org_query_data.count()
        page = page if page else 1
        limit = limit if limit else 10
        start = (page - 1) * limit
        end = start + limit
        org_query_data = org_query_data.offset(start).limit(end)

        org_query_data = org_query_data.options(
            joinedload(Models.Organization.general_info),
            joinedload(Models.Organization.address),
            joinedload(Models.Organization.contact_info),
            joinedload(Models.Organization.about_info),
            joinedload(Models.Organization.organization_settings),
        )

        organizations = org_query_data.all()

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
                    "portal_slug": org.general_info.portal_slug,
                    "organization_address": {
                        "country": org.address[0].country,
                        "country_code": org.address[0].country_code,
                    },
                }
                for org in organizations
            ],
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
                "message": "error while Verifying Admin",
                "error": str(e),
                "success": False,
            },
        )


@adminOrgRoute.put(path="/organization-setting/status", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Organization_Setting(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    id: str = Query(..., alias="id"),
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

        organization = db.query(Models.Organization).filter(Models.Organization.id == id).first()

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Organization Not Found", "success": False},
            )

        organization.status = True if not organization.status else False

        db.commit()
        db.refresh(organization)

        return {
            "message": "Organizations fetched successfully",
            "success": True,
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


@adminOrgRoute.get(path="/client-organization/details")
@limiter.limit(API_RATE_LIMITING)
async def Fetch_Client_Organization_Details(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    id: str = Query(..., alias="id"),
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

        organization = (
            db.query(Models.Organization)
            .options(
                joinedload(Models.Organization.general_info),
                joinedload(Models.Organization.address),
                joinedload(Models.Organization.contact_info),
                joinedload(Models.Organization.about_info),
                joinedload(Models.Organization.organization_settings),
            )
            .filter(Models.Organization.id == id)
            .first()
        )

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Organization Not Found", "success": False},
            )

        return {
            "message": "Info Fetched Successfully",
            "success": True,
            "data": {
                **model_to_filtered_dict(organization),
                "general_info": filter_fields(
                    organization.general_info, ["-id", "-organization_id"]
                ),
                "address": filter_fields(organization.address[0], ["-id", "-organization_id"]),
                "contact_info": [
                    filter_fields(contact_info, ["-id", "-organization_id"])
                    for contact_info in organization.contact_info
                ],
                "about_info": filter_fields(
                    organization.about_info[0], ["-id", "-organization_id"]
                ),
                "organization_settings": filter_fields(
                    organization.organization_settings[0], ["-id", "-organization_id"]
                ),
            },
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
