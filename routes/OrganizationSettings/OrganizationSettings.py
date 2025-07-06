from fastapi import APIRouter, status, HTTPException, Request, Depends, Query
from Middleware.verifyToken import verify_token
from Database.Database import db_dependencies
from typing import Optional
from RateLimiting import limiter
from dotenv import load_dotenv
import os
import json
from sqlalchemy import func, asc, desc
from SqlModels import Models
from sqlalchemy.orm import joinedload
from Helper.createModelInstance import cerate_model_instance
from Helper.helper import model_to_filtered_dict
from PydanticModels.OrganizationSettings.OrganizationSettings import AddEditHolidayPydanticModel
from datetime import datetime

orgSettings = APIRouter(prefix="/app/v1/org-setting", tags=["org-setting"])

load_dotenv(override=True)
API_RATE_LIMITING = os.getenv("API_RATE_LIMITING").strip()


@orgSettings.get("/fetch-info", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def FetchTheInfoOfTheOrganization(
    request: Request, db: db_dependencies, token: str = Depends(verify_token)
):
    try:
        #
        # *  We Will Firstly Check For The User's Authentication
        #
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        session_id = token["session_id"]

        user = (
            db.query(Models.User)
            .options(joinedload(Models.User.sessions), joinedload(Models.User.organization))
            .filter(Models.User.id == user_id)
            .first()
        )

        if not user or not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Account is deactivated. Access denied."
                        if user.account_status
                        else "User Not Found"
                    ),
                    "success": False,
                },
            )

        if not user.organization.status:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        # We Will Also Check For The Relevant Session That This Particular Session Exists Or Not

        if not any(session.id == session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
                headers={"WWW-Authenticate": "Bearer"},
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
            .filter(Models.Organization.id == user.organization_id)
            .first()
        )

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Organization Not Found", "success": False},
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "message": "Info Fetched Successfully",
            "success": True,
            "data": {
                "id": organization.id,
                "general_info": model_to_filtered_dict(organization.general_info),
                "address": model_to_filtered_dict(organization.address[0]),
                "contact_info": organization.contact_info,
                "about_info": model_to_filtered_dict(organization.about_info[0]),
                "organization_settings": model_to_filtered_dict(
                    organization.organization_settings[0]
                ),
                "status": organization.status,
                "organization_created": organization.organization_created,
                "created_at": organization.created_at,
                "updated_at": organization.updated_at,
            },
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while fetching All The Reporting Manager",
                "error": str(e),
                "success": False,
            },
        )


@orgSettings.post("/holiday/add-edit", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def AddEditHoliday(
    request: Request,
    db: db_dependencies,
    data: AddEditHolidayPydanticModel,
    token: str = Depends(verify_token),
    type: str = Query(..., description="Operation Type: add or edit", alias="type"),
    id: Optional[str] = Query(None, description="Id Is Required For The Edit Function", alias="id"),
):
    try:
        # Checking For The Valid Token
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        session_id = token["session_id"]

        if type not in ["add", "edit"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={
                    "message": "Invalid type. Must be 'add' or 'edit'",
                    "success": False,
                },
            )

        user = (
            db.query(Models.User)
            .options(joinedload(Models.User.sessions), joinedload(Models.User.organization))
            .filter(Models.User.id == user_id)
            .first()
        )

        if not user or not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Account is deactivated. Access denied."
                        if user.account_status
                        else "User Not Found"
                    ),
                    "success": False,
                },
            )
        if not user.organization.status:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        if not any(session.id == session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
                headers={"WWW-Authenticate": "Bearer"},
            )

        personal_info = (
            db.query(Models.PersonalInfo).filter(Models.PersonalInfo.user_id == user.id).first()
        )

        if type == "add":

            config_module = (
                db.query(Models.ConfigModule)
                .filter(Models.ConfigModule.organization_id == user.organization_id)
                .first()
            )

            if not config_module:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "success": False,
                        "message": "Unable To Find Config Module",
                    },
                )

            existing_holiday = (
                db.query(Models.OrganizationHolidaysSchema)
                .filter(
                    func.lower(Models.OrganizationHolidaysSchema.holiday_name)
                    == func.lower(data.holiday_name),
                    Models.OrganizationHolidaysSchema.year == data.year,
                )
                .first()
            )

            if existing_holiday:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Holiday With This Name Is Already Exist",
                        "success": False,
                    },
                )
            created_by_user = model_to_filtered_dict(
                personal_info, ["id", "first_name", "last_name"]
            )

            current_date = datetime.utcnow()
            custom_date = current_date.replace(year=data.year)

            holiday = Models.OrganizationHolidaysSchema(
                holiday_name=data.holiday_name,
                date=data.date,
                source_type="user_created",
                config_module_id=config_module.id,
                created_by=json.dumps(created_by_user),
                created_at=custom_date,
                updated_by=None,
                year=data.year,
            )
            db.add(holiday)
            db.commit()
            db.refresh(holiday)
            return {"success": True, "message": "Holiday Added Successfully"}

        else:
            if type == "edit" and not id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "ID is required for edit operation",
                        "success": False,
                    },
                )

            existing_holiday = (
                db.query(Models.OrganizationHolidaysSchema)
                .filter(
                    func.lower(Models.OrganizationHolidaysSchema.holiday_name)
                    == func.lower(data.holiday_name),
                    Models.OrganizationHolidaysSchema.id != id,
                    Models.OrganizationHolidaysSchema.year == data.year,
                )
                .first()
            )

            if existing_holiday:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Holiday With This Name Is Already Exist",
                        "success": False,
                    },
                )

            holiday = (
                db.query(Models.OrganizationHolidaysSchema)
                .filter(Models.OrganizationHolidaysSchema.id == id)
                .first()
            )

            if not holiday:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "message": "Holiday Not Found",
                        "success": False,
                    },
                )

            updated_by_user = model_to_filtered_dict(
                personal_info, ["id", "first_name", "last_name"]
            )

            current_date = datetime.utcnow()
            custom_date = current_date.replace(year=data.year)

            holiday.holiday_name = data.holiday_name
            holiday.date = data.date
            holiday.updated_by = json.dumps(updated_by_user)
            holiday.year = data.year
            holiday.updated_at = custom_date

            db.commit()
            db.refresh(holiday)

            return {"success": True, "message": "Holiday Updated Successfully"}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Add Status Right Now",
                "success": False,
                "error": str(e),
            },
        )


@orgSettings.get("/holiday/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Fetch_Holiday(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    year: str = Query(..., description="To Fetch The Holiday According To The year"),
    order: Optional[str] = Query(None, description="This Is An Optional Field", alias="order"),
    field_name: Optional[str] = Query(
        None, description="This Is An Optional Field", alias="field_name"
    ),
):
    try:
        year = int(year)
        if not order:
            order = "asc"
        #
        # *  We Will Firstly Check For The User's Authentication
        #
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        session_id = token["session_id"]

        user = (
            db.query(Models.User)
            .options(joinedload(Models.User.sessions), joinedload(Models.User.organization))
            .filter(Models.User.id == user_id)
            .first()
        )

        if not user or not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Account is deactivated. Access denied."
                        if user.account_status
                        else "User Not Found"
                    ),
                    "success": False,
                },
            )

        if not user.organization.status:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        # We Will Also Check For The Relevant Session That This Particular Session Exists Or Not
        if not any(session.id == session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
                headers={"WWW-Authenticate": "Bearer"},
            )

        #
        # *  Once The User Is Authenticated Then We Will Move Further
        #
        config_module = (
            db.query(Models.ConfigModule)
            .filter(Models.ConfigModule.organization_id == user.organization_id)
            .first()
        )

        if not config_module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Config Module Not Found",
                    "success": False,
                },
            )

        query_data = db.query(Models.OrganizationHolidaysSchema).filter(
            Models.OrganizationHolidaysSchema.config_module_id == config_module.id
        )

        column_field = getattr(Models.OrganizationHolidaysSchema, field_name, None)

        if not column_field:
            raise ValueError(f"{field_name} Not Found")

        if order == "asc":

            holidays = query_data.filter(Models.OrganizationHolidaysSchema.year == year).order_by(
                asc(column_field)
            )
        elif order == "desc":
            holidays = query_data.filter(Models.OrganizationHolidaysSchema.year == year).order_by(
                desc(column_field)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Invalid Input",
                    "success": False,
                },
            )

        return {
            "success": True,
            "message": "Holiday Fetched Successfully",
            "data": [model_to_filtered_dict(holiday) for holiday in holidays],
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Fetch Holiday",
                "success": False,
                "error": str(e),
            },
        )


@orgSettings.delete(path="/holiday/delete", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def delete_project_status(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    id: str = Query(..., description="ID for delete operation"),
):
    try:
        #
        # * We Will Firstly Check For The Users Authentication
        #
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        session_id = token["session_id"]

        user = (
            db.query(Models.User)
            .options(joinedload(Models.User.sessions), joinedload(Models.User.organization))
            .filter(Models.User.id == user_id)
            .first()
        )

        if not user or not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Account is deactivated. Access denied."
                        if user.account_status
                        else "User Not Found"
                    ),
                    "success": False,
                },
            )
        if not user.organization.status:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        # We Will Also Check For The Relevant Session That This Particular Session Exists Or Not

        if not any(session.id == session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
                headers={"WWW-Authenticate": "Bearer"},
            )

        #
        # *  Once The User Is Authenticated Then We Will Move Further
        #

        holidays = (
            db.query(Models.OrganizationHolidaysSchema)
            .filter(Models.OrganizationHolidaysSchema.id == id)
            .first()
        )
        if not holidays:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Holiday Not Found", "success": False},
            )
        db.delete(holidays)
        db.commit()

        return {"message": "Holiday Deleted Successfully", "success": True}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Delete Holiday",
                "success": False,
                "error": str(e),
            },
        )
