import json
import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.orm import joinedload
from constants.constant import SUCCESS
from config.EnvConfig import EnvConfig
from database.Database import db_dependencies
from jobs.backgroundTasks.leavesModule.LeavesModule import (
    add_leaves_balance_in_employee,
)
from middleware.UserAuthenticator import UserAuthenticatorMiddleware
from models.pydantic.OrganizationSettings.OrganizationSettings import (
    AddEditHolidayPydanticModel,
    CreateLeaveTypePydanticModel,
)
from models.sql import Models
from middleware.RateLimiting import limiter
from utils.helper.helper import filter_fields, model_to_filtered_dict
from utils.responseMessages import ERROR_MESSAGE, SUCCESS_MESSAGE

orgSettings = APIRouter(prefix="/app/v1/org-setting", tags=["org-setting"])

load_dotenv(override=True)
API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING.strip()


def has_view_access(array_of_modules, label):
    for module in array_of_modules:
        if module.module_label == label:
            if any(
                permission.label == "view" and permission.is_allowed
                for permission in module.permissions or []
            ):
                return True

        if getattr(module, "sub_modules", None):
            if has_view_access(module.sub_modules or [], label):
                return True
    return False


@orgSettings.get("/fetch-info", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def FetchTheInfoOfTheOrganization(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

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
        all_modules = (
            db.query(Models.RoleAssociatedPermissionModule)
            .filter(
                and_(
                    Models.RoleAssociatedPermissionModule.role_module_id
                    == user.employee_info.employee_role_id,
                    Models.RoleAssociatedPermissionModule.module_label == "general_info",
                )
            )
            .options(
                joinedload(Models.RoleAssociatedPermissionModule.permissions),
                joinedload(Models.RoleAssociatedPermissionModule.sub_modules),
            )
            .all()
        )

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": ERROR_MESSAGE.ORGANIZATION_NOT_FOUND, "success": SUCCESS.FALSE},
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "message": SUCCESS_MESSAGE.ORGANIZATION_INFO_FETCHED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": {
                **model_to_filtered_dict(organization),
                "general_info": (
                    filter_fields(organization.general_info, ["-id", "-organization_id"])
                    if has_view_access(all_modules, "general_information")
                    else None
                ),
                "address": (
                    filter_fields(organization.address[0], ["-id", "-organization_id"])
                    if has_view_access(all_modules, "organization_address")
                    else None
                ),
                "contact_info": (
                    [
                        filter_fields(contact_info, ["-id", "-organization_id"])
                        for contact_info in organization.contact_info
                    ]
                    if has_view_access(all_modules, "organization_contact_info")
                    else None
                ),
                "about_info": (
                    filter_fields(organization.about_info[0], ["-id", "-organization_id"])
                    if has_view_access(all_modules, "about_info")
                    else None
                ),
                "organization_settings": (
                    filter_fields(organization.organization_settings, ["-id", "-organization_id"])
                    if has_view_access(all_modules, "organization_settings_details")
                    else None
                ),
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
                "success": SUCCESS.FALSE,
            },
        )


@orgSettings.post("/holiday/add-edit", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def AddEditHoliday(
    request: Request,
    db: db_dependencies,
    data: AddEditHolidayPydanticModel,
    type: str = Query(..., description="Operation Type: add or edit", alias="type"),
    id: Optional[str] = Query(None, description="Id Is Required For The Edit Function", alias="id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        if type not in ["add", "edit"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={
                    "message": ERROR_MESSAGE.INVALID_TYPE,
                    "success": SUCCESS.FALSE,
                },
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
                        "success": SUCCESS.FALSE,
                        "message": ERROR_MESSAGE.CONFIG_MODULE_NOT_FOUND,
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
                        "message": ERROR_MESSAGE.HOLIDAY_ALREADY_EXISTS,
                        "success": SUCCESS.FALSE,
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
            return {"success": SUCCESS.TRUE, "message": SUCCESS_MESSAGE.HOLIDAY_ADDED_SUCCESSFULLY}

        else:
            if type == "edit" and not id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": ERROR_MESSAGE.ID_REQUIRED_TO_OPERATION,
                        "success": SUCCESS.FALSE,
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
                        "message": ERROR_MESSAGE.HOLIDAY_ALREADY_EXISTS,
                        "success": SUCCESS.FALSE,
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
                        "message": ERROR_MESSAGE.HOLIDAY_NOT_FOUND,
                        "success": SUCCESS.FALSE,
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

            return {"success": SUCCESS.TRUE, "message": SUCCESS_MESSAGE.HOLIDAY_EDITED_SUCCESSFULLY}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Add Status Right Now",
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )


@orgSettings.get("/holiday/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Fetch_Holiday(
    request: Request,
    db: db_dependencies,
    year: str = Query(..., description="To Fetch The Holiday According To The year"),
    order: Optional[str] = Query(None, description="This Is An Optional Field", alias="order"),
    field_name: Optional[str] = Query(
        None, description="This Is An Optional Field", alias="field_name"
    ),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        year = int(year)
        if not order:
            order = "asc"

        config_module = (
            db.query(Models.ConfigModule)
            .filter(Models.ConfigModule.organization_id == user.organization_id)
            .first()
        )

        if not config_module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": ERROR_MESSAGE.CONFIG_MODULE_NOT_FOUND,
                    "success": SUCCESS.FALSE,
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
                    "message": ERROR_MESSAGE.INVALID_SORTING_ARGUMENT,
                    "success": SUCCESS.FALSE,
                },
            )

        return {
            "success": SUCCESS.TRUE,
            "message": SUCCESS_MESSAGE.HOLIDAYS_FETCHED_SUCCESSFULLY,
            "data": [model_to_filtered_dict(holiday) for holiday in holidays],
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Fetch Holiday",
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )


@orgSettings.delete(path="/holiday/delete", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def delete_holiday(
    request: Request,
    db: db_dependencies,
    id: str = Query(..., description="ID for delete operation"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

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
                detail={"message": ERROR_MESSAGE.HOLIDAY_NOT_FOUND, "success": SUCCESS.FALSE},
            )
        db.delete(holidays)
        db.commit()

        return {"message": SUCCESS_MESSAGE.HOLIDAY_DELETED_SUCCESSFULLY, "success": SUCCESS.TRUE}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.UNABLE_TO_DELETE_HOLIDAY,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )


@orgSettings.post(path="/leaves/leave-type/create", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def create_leave_type(
    request: Request,
    db: db_dependencies,
    background_task: BackgroundTasks,
    data: CreateLeaveTypePydanticModel,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        find_leave = (
            db.query(Models.LeavesSettings)
            .filter(
                or_(
                    Models.LeavesSettings.leave_name == data.leave_name,
                    Models.LeavesSettings.leave_code == data.leave_code,
                )
            )
            .first()
        )

        if find_leave:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.LEAVE_TYPE_ALREADY_EXISTS,
                    "success": SUCCESS.FALSE,
                },
            )

        organization = (
            db.query(Models.Organization)
            .filter(Models.Organization.id == user.organization_id)
            .first()
        )

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.ORGANIZATION_NOT_FOUND,
                    "success": SUCCESS.FALSE,
                },
            )

        updated_created_by_user = model_to_filtered_dict(
            user.personal_info, ["user_id", "first_name", "last_name"]
        )

        leave_data = Models.LeavesSettings(
            leave_name=data.leave_name,
            leave_code=data.leave_code,
            is_paid=data.is_paid,
            max_number_of_leave=data.max_number_of_leave,
            refill_quarterly=data.refill_quarterly,
            refill_from=data.refill_from,
            description=data.description,
            gender=json.dumps(data.gender),
            employee_status=json.dumps(data.employee_status),
            marital_status=json.dumps(data.marital_status),
            status=data.status,
            organization_id=organization.id,
            created_by=json.dumps(updated_created_by_user),
        )

        db.add(leave_data)
        db.commit()
        db.refresh(leave_data)

        background_task.add_task(
            add_leaves_balance_in_employee,
            organization_id=organization.id,
            refill_quarterly=data.refill_quarterly,
            max_number_of_leave=data.max_number_of_leave,
            leave_type_id=leave_data.id,
        )

        return {
            "success": SUCCESS.TRUE,
            "message": f"Leave type '{leave_data.leave_name}' created successfully.",
            "data": {"leave_data": leave_data},
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.UNABLE_TO_ADD_LEAVE_TYPE,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )


@orgSettings.get(path="/leaves/leave-type/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_all_leave_types(
    request: Request, db: db_dependencies, user: dict = Depends(UserAuthenticatorMiddleware)
):
    try:
        organization = (
            db.query(Models.Organization)
            .filter(Models.Organization.id == user.organization_id)
            .first()
        )

        query_data = (
            db.query(Models.LeavesSettings)
            .filter(Models.LeavesSettings.organization_id == organization.id)
            .all()
        )

        data = [model_to_filtered_dict(_data) for _data in query_data]

        return {
            "success": SUCCESS.TRUE,
            "message": SUCCESS_MESSAGE.LEAVES_TYPE_FETCHED_SUCCESSFULLY,
            "data": data,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.UNABLE_TO_ADD_LEAVE_TYPE,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )
