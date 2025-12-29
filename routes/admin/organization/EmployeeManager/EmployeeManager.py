import json
import math
import os
from typing import Optional
from urllib.parse import unquote

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import joinedload

from config.EnvConfig import EnvConfig
from database.Database import db_dependencies
from middleware.verifyToken import verify_token
from models.sql import Models
from RateLimiting import limiter
from utils.helper.helper import filter_fields
from utils.responseMessages.AuthErrorMessage import ADMIN_NOT_FOUND

from .EmployeeQueryFilters import apply_query_filter

load_dotenv(override=True)
adminOrgEmpControl = APIRouter(prefix="/app/v1/admin/organization/employees", tags=["admin"])

API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING


@adminOrgEmpControl.get(path="/fetch-all", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Fetch_All_The_Employee_Of_The_Organization(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    id: str = Query(..., alias="id"),
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

        organization = db.query(Models.Organization).filter(Models.Organization.id == id).first()

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Organization Not Found", "success": False},
            )

        filter_data = ""

        if filter:
            decoded = unquote(filter)
            filter_data = json.loads(decoded)

        query_data = db.query(Models.User).filter(Models.User.organization_id == organization.id)

        query_data = query_data.join(Models.User.personal_info)

        query_data = query_data.outerjoin(Models.User.employee_info)

        if filter_data:
            query_data = apply_query_filter(query_data, filter_data)

        total_data = query_data.count()
        page = page if page else 1
        limit = limit if limit else 10
        start = (page - 1) * limit
        end = start + limit
        query_data = query_data.offset(start).limit(end)

        query_data = query_data.options(
            joinedload(Models.User.personal_info),
            joinedload(Models.User.employee_info)
            .joinedload(Models.EmployeeInfo.reporting_manager)
            .joinedload(Models.User.personal_info),
            joinedload(Models.User.employee_info)
            .joinedload(Models.EmployeeInfo.reporting_manager)
            .joinedload(Models.User.employee_info),
            joinedload(Models.User.employee_info).joinedload(Models.EmployeeInfo.employee_role),
        )

        employee_data = query_data.all()

        _data = []

        for employee in employee_data:
            employee_dict = filter_fields(employee, fields=["account_status", "organization_id"])
            personal_info = filter_fields(employee.personal_info) if employee.personal_info else {}
            employee_info = {}
            reporting_manager_info = {}

            if employee.employee_info:
                employee_info = filter_fields(employee.employee_info, fields=["-reporting_manager"])

                if employee.employee_info.reporting_manager:

                    reporting_manager_info = {
                        **filter_fields(employee.employee_info.reporting_manager, fields=["id"]),
                    }
                    if employee.employee_info.reporting_manager.personal_info:
                        reporting_manager_info.update(
                            filter_fields(
                                employee.employee_info.reporting_manager.personal_info,
                                fields=[
                                    "id",
                                    "first_name",
                                    "last_name",
                                    "middle_name",
                                    "profile_picture",
                                    "profile_picture_bg",
                                    "full_name",
                                    "gender",
                                ],
                            )
                        )
                    if employee.employee_info.reporting_manager.employee_info:
                        reporting_manager_info.update(
                            filter_fields(
                                employee.employee_info.reporting_manager.employee_info,
                                fields=["employee_code"],
                            )
                        )

            _data.append(
                {
                    **employee_dict,
                    "personal_info": personal_info,
                    "employee_info": {
                        **employee_info,
                        "reporting_manager": (
                            reporting_manager_info if reporting_manager_info else None
                        ),
                    },
                }
            )

        return {
            "message": "user verified successfully",
            "success": True,
            "data": _data,
            "filter_data": filter_data,
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


@adminOrgEmpControl.get(path="/employee-detail", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Fetch_Employee_Details(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    employee_id: str = Query(..., alias="employee_id"),
    organization_id: str = Query(..., alias="organization_id"),
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
            db.query(Models.Organization).filter(Models.Organization.id == organization_id).first()
        )

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Organization Not Found", "success": False},
            )

        employee_data = (
            db.query(Models.User)
            .options(
                joinedload(Models.User.personal_info),
                joinedload(Models.User.employee_info)
                .joinedload(Models.EmployeeInfo.reporting_manager)
                .joinedload(Models.User.personal_info),
                joinedload(Models.User.employee_info).joinedload(Models.EmployeeInfo.employee_role),
                joinedload(Models.User.personal_contact_info).joinedload(
                    Models.PersonalContactInfo.emergency_contacts
                ),
                joinedload(Models.User.family_info).joinedload(Models.FamilyInfo.children),
                joinedload(Models.User.current_address),
                joinedload(Models.User.permanent_address),
                joinedload(Models.User.social_link),
            )
            .filter(Models.User.id == employee_id)
            .first()
        )

        return {
            "message": "Employee Details Fetched SuccessFully",
            "success": True,
            "data": (
                {
                    **filter_fields(
                        employee_data,
                        fields=[
                            "-password",
                            "-personal_info",
                            "-personal_contact_info",
                            "-family_info",
                            "-employee_info",
                        ],
                    ),
                    "employee_info": {
                        **filter_fields(employee_data.employee_info, fields=["-reporting_manager"]),
                        "reporting_manager": (
                            {
                                **filter_fields(
                                    employee_data.employee_info.reporting_manager,
                                    fields=["id"],
                                ),
                                **(
                                    filter_fields(
                                        employee_data.employee_info.reporting_manager.personal_info,
                                        fields=[
                                            "-id",
                                            "first_name",
                                            "last_name",
                                            "middle_name",
                                            "profile_picture",
                                            "profile_picture_bg",
                                            "full_name",
                                            "gender",
                                        ],
                                    )
                                    if employee_data.employee_info.reporting_manager
                                    and employee_data.employee_info.reporting_manager.personal_info
                                    else {}
                                ),
                            }
                            if employee_data.employee_info
                            and employee_data.employee_info.reporting_manager
                            else {}
                        ),
                    },
                    "personal_info": (
                        filter_fields(employee_data.personal_info)
                        if employee_data.personal_info
                        else {}
                    ),
                    "personal_contact_info": (
                        filter_fields(employee_data.personal_contact_info)
                        if employee_data.personal_contact_info
                        else {}
                    ),
                    "family_info": (
                        filter_fields(employee_data.family_info[0])
                        if employee_data.family_info
                        else {}
                    ),
                }
                if employee_data
                else None
            ),
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


@adminOrgEmpControl.put(path="/disable-employee", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def name(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    employee_id: str = Query(..., alias="employee_id"),
    organization_id: str = Query(..., alias="organization_id"),
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

        employee = db.query(Models.User).filter(Models.User.id == employee_id).first()

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "User Not Found", "success": False},
            )

        if not employee.organization_id == organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "User's org ID does not match.", "success": False},
            )

        employee.account_status = True if not employee.account_status else False

        db.commit()
        db.refresh(employee)

        return {"message": "User's Account Status Updated SuccessFully", "success": False}

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
