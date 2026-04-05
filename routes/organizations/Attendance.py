import json
import math
import os
import uuid
from datetime import date, datetime
from tracemalloc import start
from typing import List, Optional
from urllib.parse import unquote

import cloudinary
import cloudinary.uploader
import pandas as pd
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import joinedload

from config.EnvConfig import EnvConfig
from constants.constant import SUCCESS
from database.Database import db_dependencies
from middleware.RateLimiting import limiter
from middleware.UserAuthenticator import UserAuthenticatorMiddleware
from models.pydantic.Organizations.AttendancePydanticModal import (
    AttendancePunchInPydantic,
)
from models.sql import Models
from utils.helper.calculateDistanceWithHaversine import calculateDistanceWithHaversine
from utils.helper.helper import filter_fields, model_to_filtered_dict, parse_to_utc_date
from utils.responseMessages import ERROR_MESSAGE, SUCCESS_MESSAGE

from .AttendanceLeaveQueryFilter import (
    attendance_leave_team_organization_query_filter,
    attendance_self_leave_quey_filter,
)

attendanceRoute = APIRouter(prefix="/app/v1/attendance", tags=["Attendance"])

API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING


cloudinary.config(
    cloud_name=EnvConfig.CLOUDINARY_CLOUD_NAME,
    api_key=EnvConfig.CLOUDINARY_API_KEY,
    api_secret=EnvConfig.CLOUDINARY_API_SECRET,
)


def upload_leave_documents_function(upload_file: UploadFile):
    unique_public_id = str(uuid.uuid4())
    folder = "leave_documents"
    file_name = upload_file.filename

    result = cloudinary.uploader.upload(
        upload_file.file,
        resource_type="auto",
        public_id=unique_public_id,
        folder=folder,
    )

    public_id = result["public_id"]

    media_asset_url = (
        f"{EnvConfig.ORBITRMS_MEDIA_SERVICE_BASE_URL}/{folder}/{unique_public_id}/{file_name}"
    )

    return {
        "asset_id": result["asset_id"],
        "public_id": public_id,
        "file_name": file_name,
        "file_type": upload_file.content_type,
        "folder": folder,
        "original_url": result["secure_url"],
        "media_asset_url": media_asset_url,
    }


# The APi To Apply The Leave By The Self
@attendanceRoute.post("/apply/leave", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def handel_apply_leave(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    leave_type_id: str = Form(...),
    start_date: str = Form(...),
    start_half: str = Form(...),
    end_date: str = Form(...),
    end_half: str = Form(...),
    current_date: str = Form(...),
    description: str = Form(None),
    notify_to: Optional[List[str]] = Form(None),
    documents: Optional[List[UploadFile]] = File(None),
    employee_id: Optional[str] = Query(None, alias="employee-id"),
):
    try:

        start_date_utc = parse_to_utc_date(start_date)
        end_date_utc = parse_to_utc_date(end_date)
        current_date_utc = parse_to_utc_date(current_date)

        query_id = employee_id if employee_id else user.id

        existing_leaves = (
            db.query(Models.AttendanceLeavesModule)
            .filter(
                Models.AttendanceLeavesModule.user_id == query_id,
                Models.AttendanceLeavesModule.status != "rejected",
                Models.AttendanceLeavesModule.start_date <= end_date,
                Models.AttendanceLeavesModule.end_date >= start_date,
            )
            .all()
        )

        for applied_leave in existing_leaves:
            if applied_leave.start_date == start_date and applied_leave.end_date == end_date:
                if applied_leave.start_half == "first_half" and start_half == "first_half":
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": ERROR_MESSAGE.LEAVE_REQUEST_ALREADY_APPLIED,
                            "success": SUCCESS.FALSE,
                        },
                    )
                if applied_leave.end_half == "second_half" and end_half == "second_half":
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": ERROR_MESSAGE.LEAVE_REQUEST_ALREADY_APPLIED,
                            "success": SUCCESS.FALSE,
                        },
                    )
                if (
                    applied_leave.start_half == "first_half"
                    and applied_leave.end_half == "second_half"
                ):
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": ERROR_MESSAGE.LEAVE_REQUEST_ALREADY_APPLIED,
                            "success": SUCCESS.FALSE,
                        },
                    )

        employee_info = db.query(Models.User).filter(Models.User.id == query_id).first()

        if not employee_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": ERROR_MESSAGE.EMPLOYEE_NOT_FOUND,
                    "success": SUCCESS.FALSE,
                },
            )

        leave_type = (
            db.query(Models.LeavesSettings)
            .filter(
                Models.LeavesSettings.id == leave_type_id,
                Models.LeavesSettings.organization_id == user.organization_id,
                Models.LeavesSettings.status == True,
            )
            .first()
        )

        if not leave_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.NO_LEAVE_TYPE_FOUND,
                    "success": SUCCESS.FALSE,
                },
            )

        updated_created_by_user = model_to_filtered_dict(
            user.personal_info, ["user_id", "first_name", "last_name"]
        )

        difference_btw_date = (start_date_utc - current_date_utc).days
        is_planned = difference_btw_date > 5

        if start_date_utc == end_date_utc:

            if start_half == end_half:
                total_days = 0.5
            elif start_half == "first_half" and end_half == "second_half":
                total_days = 1
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Invalid leave half selection for same day",
                        "success": SUCCESS.FALSE,
                    },
                )
        else:

            total_days = (end_date_utc - start_date_utc).days + 1

            if start_half == "second_half":
                total_days -= 0.5

            if end_half == "first_half":
                total_days -= 0.5

        leave_type = (
            db.query(Models.LeaveBalance)
            .filter(
                Models.LeaveBalance.leave_type_id == leave_type_id,
                Models.LeaveBalance.user_id == query_id,
            )
            .first()
        )

        if not leave_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.NO_LEAVE_TYPE_FOUND,
                    "success": SUCCESS.FALSE,
                },
            )

        if leave_type.available_leaves < total_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Insufficient leave balance. You cannot apply for more than your available leaves.",
                    "success": SUCCESS.FALSE,
                },
            )

        uploaded_documents = []

        if documents:
            uploaded_documents = [
                await run_in_threadpool(upload_leave_documents_function, doc) for doc in documents
            ]

        notify_to_users_array = []

        if notify_to:

            for employee_id in notify_to:
                print("employee_id", employee_id)
                user_info = db.query(Models.User).filter(Models.User.id == employee_id).first()

                if user_info:
                    notify_to_users_array.append(user_info)

        leave_info = Models.AttendanceLeavesModule(
            leave_type_id=leave_type_id,
            start_date=start_date,
            start_half=start_half,
            is_planned=is_planned,
            end_date=end_date,
            end_half=end_half,
            description=description,
            notify_to_users=notify_to_users_array,
            documents=json.dumps(uploaded_documents),
            total_days=total_days,
            status="pending",
            user_id=query_id,
            created_by=json.dumps(updated_created_by_user),
        )

        db.add(leave_info)

        leave_type.available_leaves = leave_type.available_leaves - total_days

        db.commit()

        return {
            "message": SUCCESS_MESSAGE.LEAVE_APPLIED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_APPLYING_LEAVE,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


# The Api For The Editing The Api By The Self
@attendanceRoute.put("/edit/leave", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def handel_edit_leave(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    pass


@attendanceRoute.get("/fetch/leaves", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_users_leave(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    page: int = Query(..., alias="page"),
    limit: int = Query(..., alias="limit"),
    filter: Optional[str] = Query(None, alias="filter"),
):
    try:
        filter_data = ""
        if filter:
            decoded = unquote(filter)
            filter_data = json.loads(decoded)

        employee_data = (
            db.query(Models.User)
            .options(
                joinedload(Models.User.personal_info),
                joinedload(Models.User.employee_info)
                .joinedload(Models.EmployeeInfo.reporting_manager)
                .joinedload(Models.User.personal_info),
                joinedload(Models.User.employee_info)
                .joinedload(Models.EmployeeInfo.reporting_manager)
                .joinedload(Models.User.employee_info),
            )
            .filter(Models.User.id == user.id)
            .first()
        )

        leave_query = (
            db.query(Models.AttendanceLeavesModule)
            .options(joinedload(Models.AttendanceLeavesModule.leave_type))
            .filter(Models.AttendanceLeavesModule.user_id == user.id)
            .order_by(Models.AttendanceLeavesModule.created_at.desc())
        )

        total_data = leave_query.count()
        page = page if page else 1
        limit = limit if limit else 10

        leaves = leave_query.offset((page - 1) * limit).limit(limit).all()

        _data = []

        for data in leaves:
            if filter_data:
                if not attendance_self_leave_quey_filter(data, filter=filter_data):
                    continue
            _data.append(
                {
                    **filter_fields(data, fields=["-leave_type", "-notify_to_id"]),
                    "leave_name": data.leave_type.leave_name,
                    "leave_code": data.leave_type.leave_code,
                    "notify_to_users": [
                        {
                            **filter_fields(
                                notify_user.personal_info,
                                fields=["first_name", "middle_name", "last_name", "full_name"],
                            ),
                            **filter_fields(
                                notify_user.employee_info,
                                fields=["employee_code"],
                            ),
                            "id": notify_user.id,
                        }
                        for notify_user in data.notify_to_users
                    ],
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
                                    ],
                                )
                                if employee_data.employee_info.reporting_manager
                                and employee_data.employee_info.reporting_manager.personal_info
                                else {}
                            ),
                            **(
                                filter_fields(
                                    employee_data.employee_info.reporting_manager.employee_info,
                                    fields=[
                                        "employee_code",
                                    ],
                                )
                                if employee_data.employee_info.reporting_manager
                                and employee_data.employee_info.reporting_manager.employee_info
                                else {}
                            ),
                        }
                        if employee_data.employee_info
                        and employee_data.employee_info.reporting_manager
                        else {}
                    ),
                }
            )

        return {
            "message": SUCCESS_MESSAGE.USER_VERIFIED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": _data,
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
                "message": ERROR_MESSAGE.ERROR_WHILE_APPLYING_LEAVE,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.get("/fetch-all/leaves", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_leaves(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    org_id: str = Query(..., alias="org-id"),
    query_date: date = Query(..., alias="date"),
):
    try:
        query_data = db.query(Models.User).filter(Models.User.organization_id == org_id).all()

        users_data = []

        for data in query_data:
            if data.applied_leaves:
                for leave in data.applied_leaves:
                    if leave.start_date <= query_date <= leave.end_date:
                        users_data.append(leave)

        return {
            "message": SUCCESS_MESSAGE.LEAVES_FETCHED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": users_data,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_APPLYING_LEAVE,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.get("/fetch/leave-balance", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_all_leave_balance(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    employee_id: Optional[str] = Query(None, alias="employee-id"),
):
    try:
        query_id = employee_id if employee_id else user.id
        query_data = (
            db.query(Models.LeaveBalance).filter(Models.LeaveBalance.user_id == query_id).all()
        )

        data = []

        for _data in query_data:
            available_gender = (
                json.loads(_data.leave_type.gender) if _data.leave_type.gender else []
            )
            available_emp_status = (
                json.loads(_data.leave_type.employee_status)
                if _data.leave_type.employee_status
                else []
            )
            marital_status = (
                json.loads(_data.leave_type.marital_status)
                if _data.leave_type.marital_status
                else []
            )

            if (
                user.personal_info.gender in available_gender
                and user.employee_info.status in available_emp_status
                and user.family_info[0].marital_status in marital_status
            ):

                if _data.leave_type.status:
                    data.append(
                        {
                            **filter_fields(_data, ["-leave_type", "-last_refill_date"]),
                            **filter_fields(
                                _data.leave_type,
                                [
                                    "-updated_at",
                                    "-updated_by",
                                    "-created_by",
                                    "-created_at",
                                    "-refill_quarterly",
                                    "-refill_from",
                                ],
                            ),
                        }
                    )

        return {
            "message": SUCCESS_MESSAGE.LEAVES_FETCHED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": data,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_FETCHING_LEAVE_BALANCE,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.get("/fetch/team/leaves", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_users_leave(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    page: int = Query(..., alias="page"),
    limit: int = Query(..., alias="limit"),
    filter: Optional[str] = Query(None, alias="filter"),
):
    try:

        filter_data = ""
        if filter:
            decoded = unquote(filter)
            filter_data = json.loads(decoded)

        _data = []

        team_data = (
            db.query(Models.User)
            .options(
                joinedload(Models.User.personal_info),
                joinedload(Models.User.applied_leaves).joinedload(
                    Models.AttendanceLeavesModule.leave_type
                ),
                joinedload(Models.User.employee_info)
                .joinedload(Models.EmployeeInfo.reporting_manager)
                .joinedload(Models.User.personal_info),
            )
            .filter(Models.User.employee_info.has(reporting_to_id=user.id))
            .all()
        )

        today = date.today()
        employees_on_leave = set()
        planned_leaves = set()
        unplanned_leaves = set()
        pending_leaves = set()
        cancelled_leaves = set()

        for employee in team_data:
            for leave in employee.applied_leaves:

                employee_id = employee.id
                if filter_data:
                    if not attendance_leave_team_organization_query_filter(
                        leave, employee_id, filter=filter_data
                    ):
                        continue

                start_date_utc = parse_to_utc_date(leave.start_date)
                end_date_utc = parse_to_utc_date(leave.end_date)

                if start_date_utc <= today <= end_date_utc:
                    if leave.status not in ["cancelled", "rejected"]:
                        employees_on_leave.add(employee.id)

                if leave.is_planned:
                    planned_leaves.add(leave.id)
                else:
                    unplanned_leaves.add(leave.id)

                if leave.status == "pending":
                    pending_leaves.add(leave.id)

                if leave.status == "cancelled":
                    cancelled_leaves.add(leave.id)

                _data.append(
                    {
                        **filter_fields(
                            leave,
                            fields=[
                                "-leave_type",
                                "-notify_to_id",
                            ],
                        ),
                        "leave_name": leave.leave_type.leave_name,
                        "leave_code": leave.leave_type.leave_code,
                        "employee_info": {
                            "id": employee.id,
                            **(
                                filter_fields(
                                    employee.personal_info,
                                    fields=[
                                        "-id",
                                        "first_name",
                                        "last_name",
                                        "middle_name",
                                        "profile_picture",
                                        "profile_picture_bg",
                                        "full_name",
                                    ],
                                )
                                if employee.personal_info
                                else {}
                            ),
                            **(
                                filter_fields(
                                    employee.employee_info,
                                    fields=[
                                        "employee_code",
                                    ],
                                )
                                if employee.employee_info
                                else {}
                            ),
                        },
                        "reporting_manager": (
                            {
                                **filter_fields(
                                    employee.employee_info.reporting_manager,
                                    fields=["id"],
                                ),
                                **(
                                    filter_fields(
                                        employee.employee_info.reporting_manager.personal_info,
                                        fields=[
                                            "-id",
                                            "first_name",
                                            "last_name",
                                            "middle_name",
                                            "profile_picture",
                                            "profile_picture_bg",
                                            "full_name",
                                        ],
                                    )
                                    if employee.employee_info.reporting_manager
                                    and employee.employee_info.reporting_manager.personal_info
                                    else {}
                                ),
                                **(
                                    filter_fields(
                                        employee.employee_info.reporting_manager.employee_info,
                                        fields=[
                                            "employee_code",
                                        ],
                                    )
                                    if employee.employee_info.reporting_manager
                                    and employee.employee_info.reporting_manager.employee_info
                                    else {}
                                ),
                            }
                            if employee.employee_info and employee.employee_info.reporting_manager
                            else {}
                        ),
                        "notify_to_users": [
                            {
                                **filter_fields(
                                    notify_user.personal_info,
                                    fields=["first_name", "middle_name", "last_name", "full_name"],
                                ),
                                **filter_fields(
                                    notify_user.employee_info,
                                    fields=["employee_code"],
                                ),
                                "id": notify_user.id,
                            }
                            for notify_user in leave.notify_to_users
                        ],
                    }
                )

        total_data = len(_data)
        sorted_data = sorted(_data, key=lambda x: x["created_at"], reverse=True)
        page = page if page else 1
        limit = limit if limit else 10
        start = (page - 1) * limit
        end = start + limit
        query_data = sorted_data[start:end]

        return {
            "message": SUCCESS_MESSAGE.USER_VERIFIED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": {
                "applied_leaves": query_data,
                "team_summary": {
                    "total_employees": len(team_data),
                    "employees_on_leave": len(employees_on_leave),
                    "planned_leaves": len(planned_leaves),
                    "unplanned_leaves": len(unplanned_leaves),
                    "pending_leaves": len(pending_leaves),
                    "cancelled_leaves": len(cancelled_leaves),
                },
            },
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
                "message": ERROR_MESSAGE.ERROR_WHILE_APPLYING_LEAVE,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.get("/fetch/organization/leaves", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_users_leave(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    page: int = Query(..., alias="page"),
    limit: int = Query(..., alias="limit"),
    filter: Optional[str] = Query(None, alias="filter"),
):
    try:
        _data = []

        filter_data = ""
        if filter:
            decoded = unquote(filter)
            filter_data = json.loads(decoded)

        org_team_data = (
            db.query(Models.User)
            .options(
                joinedload(Models.User.personal_info),
                joinedload(Models.User.applied_leaves).joinedload(
                    Models.AttendanceLeavesModule.leave_type
                ),
                joinedload(Models.User.employee_info)
                .joinedload(Models.EmployeeInfo.reporting_manager)
                .joinedload(Models.User.personal_info),
            )
            .filter(Models.User.organization_id == user.organization_id)
            .all()
        )

        today = date.today()
        employees_on_leave = set()
        planned_leaves = set()
        unplanned_leaves = set()
        pending_leaves = set()
        cancelled_leaves = set()

        for employee in org_team_data:
            for leave in employee.applied_leaves:

                employee_id = employee.id
                if filter_data:
                    if not attendance_leave_team_organization_query_filter(
                        leave, employee_id, filter=filter_data
                    ):
                        continue

                start_date_utc = parse_to_utc_date(leave.start_date)
                end_date_utc = parse_to_utc_date(leave.end_date)

                if start_date_utc <= today <= end_date_utc:
                    if leave.status not in ["cancelled", "rejected"]:
                        employees_on_leave.add(employee.id)

                if leave.is_planned:
                    planned_leaves.add(leave.id)
                else:
                    unplanned_leaves.add(leave.id)

                if leave.status == "pending":
                    pending_leaves.add(leave.id)

                if leave.status == "cancelled":
                    cancelled_leaves.add(leave.id)

                _data.append(
                    {
                        **filter_fields(
                            leave,
                            fields=[
                                "-leave_type",
                                "-notify_to_id",
                            ],
                        ),
                        "leave_name": leave.leave_type.leave_name,
                        "leave_code": leave.leave_type.leave_code,
                        "employee_info": {
                            "id": employee.id,
                            **(
                                filter_fields(
                                    employee.personal_info,
                                    fields=[
                                        "-id",
                                        "first_name",
                                        "last_name",
                                        "middle_name",
                                        "profile_picture",
                                        "profile_picture_bg",
                                        "full_name",
                                    ],
                                )
                                if employee.personal_info
                                else {}
                            ),
                            **(
                                filter_fields(
                                    employee.employee_info,
                                    fields=[
                                        "employee_code",
                                    ],
                                )
                                if employee.employee_info
                                else {}
                            ),
                        },
                        "reporting_manager": (
                            {
                                **filter_fields(
                                    employee.employee_info.reporting_manager,
                                    fields=["id"],
                                ),
                                **(
                                    filter_fields(
                                        employee.employee_info.reporting_manager.personal_info,
                                        fields=[
                                            "-id",
                                            "first_name",
                                            "last_name",
                                            "middle_name",
                                            "profile_picture",
                                            "profile_picture_bg",
                                            "full_name",
                                        ],
                                    )
                                    if employee.employee_info.reporting_manager
                                    and employee.employee_info.reporting_manager.personal_info
                                    else {}
                                ),
                                **(
                                    filter_fields(
                                        employee.employee_info.reporting_manager.employee_info,
                                        fields=[
                                            "employee_code",
                                        ],
                                    )
                                    if employee.employee_info.reporting_manager
                                    and employee.employee_info.reporting_manager.employee_info
                                    else {}
                                ),
                            }
                            if employee.employee_info and employee.employee_info.reporting_manager
                            else {}
                        ),
                        "notify_to_users": [
                            {
                                **filter_fields(
                                    notify_user.personal_info,
                                    fields=["first_name", "middle_name", "last_name", "full_name"],
                                ),
                                **filter_fields(
                                    notify_user.employee_info,
                                    fields=["employee_code"],
                                ),
                                "id": notify_user.id,
                            }
                            for notify_user in leave.notify_to_users
                        ],
                    }
                )

        total_data = len(_data)
        sorted_data = sorted(_data, key=lambda x: x["created_at"], reverse=True)
        page = page if page else 1
        limit = limit if limit else 10
        start = (page - 1) * limit
        end = start + limit
        query_data = sorted_data[start:end]

        return {
            "message": SUCCESS_MESSAGE.USER_VERIFIED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": {
                "applied_leaves": query_data,
                "team_summary": {
                    "total_employees": len(org_team_data),
                    "employees_on_leave": len(employees_on_leave),
                    "planned_leaves": len(planned_leaves),
                    "unplanned_leaves": len(unplanned_leaves),
                    "pending_leaves": len(pending_leaves),
                    "cancelled_leaves": len(cancelled_leaves),
                },
            },
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
                "message": ERROR_MESSAGE.ERROR_WHILE_APPLYING_LEAVE,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.put("/leave-request/update", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def update_leave_request(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    leave_status: str = Query(..., alias="status"),
    leave_id: str = Query(..., alias="id"),
):
    try:
        query_data = (
            db.query(Models.AttendanceLeavesModule)
            .options(joinedload(Models.AttendanceLeavesModule.user))
            .filter(Models.AttendanceLeavesModule.id == leave_id)
        ).first()

        reporting_manager_id = query_data.user.employee_info.reporting_to_id

        if query_data.status in ["rejected", "cancelled"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={
                    "message": ERROR_MESSAGE.LEAVE_REQUEST_NOT_ALLOWED,
                    "success": SUCCESS.FALSE,
                },
            )

        if not reporting_manager_id == user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": ERROR_MESSAGE.NOT_AUTHORIZED_TO_MANAGE_LEAVE_UPDATE,
                    "success": SUCCESS.FALSE,
                },
            )

        if not leave_status in ["pending", "approved", "rejected", "cancelled"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": ERROR_MESSAGE.PLEASE_PROVIDE_APPROPRIATE_LEAVE_STATUS,
                    "success": SUCCESS.FALSE,
                },
            )

        updated_created_by_user = model_to_filtered_dict(
            user.personal_info, ["user_id", "first_name", "last_name"]
        )

        query_data.status = leave_status
        query_data.updated_by = json.dumps(updated_created_by_user)

        if leave_status in ["rejected", "cancelled"]:
            leave_balance = (
                db.query(Models.LeaveBalance)
                .filter(
                    Models.LeaveBalance.leave_type_id == query_data.leave_type_id,
                    Models.LeaveBalance.user_id == query_data.user_id,
                )
                .first()
            )

            if not leave_balance:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "message": ERROR_MESSAGE.LEAVE_BALANCE_NOT_FOUND,
                        "success": SUCCESS.FALSE,
                    },
                )

            leave_balance.available_leaves += query_data.total_days

        db.commit()

        return {
            "message": f"Leave {leave_status} Successfully",
            "success": SUCCESS.TRUE,
            "data": {},
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_APPLYING_LEAVE,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.get("/fetch/leave-types", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_all_leave_type(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        query_data = (
            db.query(Models.LeavesSettings)
            .filter(Models.LeavesSettings.organization_id == user.organization_id)
            .all()
        )

        _data = []

        for data in query_data:
            _data.append(data.leave_code)

        return {
            "message": SUCCESS_MESSAGE.USER_VERIFIED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": _data,
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_APPLYING_LEAVE,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.post("/punch-in", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def AttendancePunchIn(
    request: Request,
    db: db_dependencies,
    data: AttendancePunchInPydantic,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        active_session = (
            db.query(Models.AttendancePunchInOutModule)
            .filter(
                Models.AttendancePunchInOutModule.user_id == user.id,
                Models.AttendancePunchInOutModule.status == "active",
            )
            .first()
        )

        if active_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.ACTIVE_ATTENDANCE_SESSION_FOUND,
                    "success": SUCCESS.FALSE,
                },
            )
        query_data = (
            db.query(Models.OrganizationLocationsConfig)
            .filter(Models.OrganizationLocationsConfig.organization_id == user.organization_id)
            .all()
        )

        if not query_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.NO_LOCATION_CONFIG_ADDED,
                    "error": str(e),
                    "success": SUCCESS.FALSE,
                },
            )
        is_with_in_range = False
        if not data.is_work_from_home:
            for location_config in query_data:

                user_location_coordinates = {
                    "latitude": (
                        data.location_coordinates.get("latitude")
                        if isinstance(data.location_coordinates, dict)
                        else data.location_coordinates.latitude
                    ),
                    "longitude": (
                        data.location_coordinates.get("longitude")
                        if isinstance(data.location_coordinates, dict)
                        else data.location_coordinates.longitude
                    ),
                }

                org_location_coordinates = json.loads(location_config.location_coordinates)

                allowed_radius_meters = (
                    location_config.allowed_radius_meters
                    if location_config.allowed_radius_meters
                    else 500
                )

                distance = calculateDistanceWithHaversine(
                    userLocation={
                        "latitude": user_location_coordinates["latitude"],
                        "longitude": user_location_coordinates["longitude"],
                    },
                    orgLocation={
                        "latitude": org_location_coordinates["latitude"],
                        "longitude": org_location_coordinates["longitude"],
                    },
                )

                if distance <= allowed_radius_meters:
                    is_with_in_range = True
                    break
                else:
                    continue

            if is_with_in_range:
                attendance_data = Models.AttendancePunchInOutModule(
                    user_id=user.id,
                    punch_in_time=datetime.utcnow(),
                    punch_in_coordinates=json.dumps(data.location_coordinates.model_dump()),
                    is_work_from_home=data.is_work_from_home,
                    status="active",
                )
                db.add(attendance_data)
                db.commit()
                db.refresh(attendance_data)

                return {
                    "message": SUCCESS_MESSAGE.ATTENDANCE_PUNCH_IN_SUCCESSFULLY,
                    "success": SUCCESS.TRUE,
                    "data": {
                        "attendance_id": attendance_data.id,
                        "punch_in_time": attendance_data.punch_in_time,
                    },
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": ERROR_MESSAGE.OUT_OF_RANGE_ATTENDANCE_PUNCH,
                        "success": SUCCESS.FALSE,
                    },
                )
        else:
            attendance_data = Models.AttendancePunchInOutModule(
                user_id=user.id,
                punch_in_time=datetime.utcnow(),
                punch_in_coordinates=json.dumps(data.location_coordinates.model_dump()),
                is_work_from_home=data.is_work_from_home,
                status="active",
            )
            db.add(attendance_data)
            db.commit()
            db.refresh(attendance_data)

            return {
                "message": SUCCESS_MESSAGE.ATTENDANCE_PUNCH_IN_SUCCESSFULLY,
                "success": SUCCESS.TRUE,
                "data": {
                    "attendance_id": attendance_data.id,
                    "punch_in_time": attendance_data.punch_in_time,
                },
            }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_APPLYING_LEAVE,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.get("/attendance-status", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def punch_in_out_status(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        active_session = (
            db.query(Models.AttendancePunchInOutModule)
            .filter(
                Models.AttendancePunchInOutModule.user_id == user.id,
                Models.AttendancePunchInOutModule.status == "active",
            )
            .first()
        )

        if not active_session:
            last_session = (
                db.query(Models.AttendancePunchInOutModule)
                .filter(Models.AttendancePunchInOutModule.user_id == user.id)
                .order_by(Models.AttendancePunchInOutModule.punch_in_time.desc())
                .first()
            )

            if not last_session:
                return {
                    "message": SUCCESS_MESSAGE.NO_ACTIVE_ATTENDANCE_SESSION,
                    "success": SUCCESS.TRUE,
                }

            last_session_break_minutes = 0

            for data in last_session.attendance_breaks:
                if data.break_duration:
                    last_session_break_minutes += data.break_duration
                elif data.break_start_time and not data.break_end_time:
                    break_start_time = data.break_start_time

                    if isinstance(break_start_time, str):
                        break_start_time = datetime.fromisoformat(break_start_time)

                    now = datetime.utcnow()
                    active_break_minutes = (now - break_start_time).total_seconds() / 60
                    last_session_break_minutes += active_break_minutes

            last_session_break_hours = int(last_session_break_minutes) / 60

            return {
                "message": SUCCESS_MESSAGE.NO_ACTIVE_ATTENDANCE_SESSION,
                "success": SUCCESS.TRUE,
                "data": {
                    "last_session": {
                        "is_punched_in": False,
                        "is_on_break": False,
                        "punch_in_time": last_session.punch_in_time,
                        "punch_out_time": last_session.punch_out_time,
                        "total_break_hours": last_session_break_hours,
                        "status": last_session.status,
                    },
                },
            }

        is_on_break: bool = False

        for breaks in active_session.attendance_breaks:
            if breaks.status == "active":
                is_on_break = True
                break

        total_break_minutes = 0

        for b in active_session.attendance_breaks:
            if b.break_duration:
                total_break_minutes += b.break_duration
            elif b.break_start_time and not b.break_end_time:
                break_start_time = b.break_start_time
                if isinstance(break_start_time, str):
                    break_start_time = datetime.fromisoformat(break_start_time)
                now = datetime.utcnow()  # or datetime.now() based on your timezone handling
                active_break_minutes = (now - break_start_time).total_seconds() / 60
                total_break_minutes += active_break_minutes

        total_break_hours = int(total_break_minutes) / 60

        return {
            "message": SUCCESS_MESSAGE.ATTENDANCE_SESSION_ACTIVE,
            "success": SUCCESS.TRUE,
            "data": {
                "current_session": {
                    "is_punched_in": True,
                    "is_on_break": is_on_break,
                    "punch_in_time": active_session.punch_in_time,
                    "total_break_hours": total_break_hours,
                }
            },
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_FETCHING_ATTENDANCE_STATUS,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.get("/punch-in-out/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def punch_in_out_status(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    month: int | None = Query(None, ge=1, le=12),
    year: int | None = Query(None),
):
    try:
        current_date = datetime.utcnow()
        target_year = year if year else current_date.year
        target_month = month if month else current_date.month

        start_of_month = datetime(target_year, target_month, 1)

        # handle December edge case
        if target_month == 12:
            end_of_month = datetime(target_year + 1, 1, 1)
        else:
            end_of_month = datetime(target_year, target_month + 1, 1)

        monthly_data = (
            db.query(Models.AttendancePunchInOutModule)
            .filter(
                Models.AttendancePunchInOutModule.user_id == user.id,
                Models.AttendancePunchInOutModule.punch_in_time >= start_of_month,
                Models.AttendancePunchInOutModule.punch_in_time < end_of_month,
            )
            .order_by(Models.AttendancePunchInOutModule.punch_in_time.desc())
            .all()
        )

        return {
            "message": SUCCESS_MESSAGE.ATTENDANCE_SESSION_ACTIVE,
            "success": SUCCESS.TRUE,
            "data": [
                {
                    **model_to_filtered_dict(session, ["-attendance_breaks"]),
                    "breaks": [
                        {**model_to_filtered_dict(attendance_break)}
                        for attendance_break in session.attendance_breaks
                    ],
                }
                for session in monthly_data
                if session is not None
            ],
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_FETCHING_ATTENDANCE_STATUS,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.post("/break/start-break", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def startBreak(
    request: Request,
    db: db_dependencies,
    data: AttendancePunchInPydantic,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        active_session = (
            db.query(Models.AttendancePunchInOutModule)
            .filter(
                Models.AttendancePunchInOutModule.user_id == user.id,
                Models.AttendancePunchInOutModule.status == "active",
            )
            .first()
        )

        if not active_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.NO_ACTIVE_ATTENDANCE_SESSION,
                    "success": SUCCESS.FALSE,
                },
            )

        active_break = (
            db.query(Models.AttendanceBreakModel)
            .filter(
                Models.AttendanceBreakModel.session_id == active_session.id,
                Models.AttendanceBreakModel.status == "active",
            )
            .first()
        )

        if active_break:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.CANT_ACTIVE_BECAUSE_ACTIVE_BREAK_FOUND,
                    "success": SUCCESS.FALSE,
                },
            )

        location_query_data = (
            db.query(Models.OrganizationLocationsConfig)
            .filter(Models.OrganizationLocationsConfig.organization_id == user.organization_id)
            .all()
        )

        if not location_query_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.NO_LOCATION_CONFIG_ADDED,
                    "error": str(e),
                    "success": SUCCESS.FALSE,
                },
            )

        is_with_in_range = False

        for location_config in location_query_data:

            user_location_coordinates = {
                "latitude": (
                    data.location_coordinates.get("latitude")
                    if isinstance(data.location_coordinates, dict)
                    else data.location_coordinates.latitude
                ),
                "longitude": (
                    data.location_coordinates.get("longitude")
                    if isinstance(data.location_coordinates, dict)
                    else data.location_coordinates.longitude
                ),
            }

            org_location_coordinates = json.loads(location_config.location_coordinates)

            allowed_radius_meters = (
                location_config.allowed_radius_meters
                if location_config.allowed_radius_meters
                else 500
            )

            distance = calculateDistanceWithHaversine(
                userLocation={
                    "latitude": user_location_coordinates["latitude"],
                    "longitude": user_location_coordinates["longitude"],
                },
                orgLocation={
                    "latitude": org_location_coordinates["latitude"],
                    "longitude": org_location_coordinates["longitude"],
                },
            )

            if distance <= allowed_radius_meters:
                is_with_in_range = True
                break
            else:
                continue

        if is_with_in_range:

            brake_data = Models.AttendanceBreakModel(
                session_id=active_session.id,
                break_start_time=datetime.utcnow(),
                status="active",
                punch_in_coordinates=json.dumps(data.location_coordinates.model_dump()),
            )
            db.add(brake_data)
            db.commit()
            db.refresh(brake_data)
            return {
                "message": SUCCESS_MESSAGE.BREAK_STARTED_SUCCESSFULLY,
                "success": SUCCESS.TRUE,
                "data": {
                    "break_id": brake_data.id,
                    "break_start_time": brake_data.break_start_time,
                },
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.OUT_OF_RANGE_ATTENDANCE_PUNCH,
                    "success": SUCCESS.FALSE,
                },
            )

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_FETCHING_ATTENDANCE_STATUS,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.post("/break/end-break", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def endBreak(
    request: Request,
    db: db_dependencies,
    data: AttendancePunchInPydantic,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        active_session = (
            db.query(Models.AttendancePunchInOutModule)
            .filter(
                Models.AttendancePunchInOutModule.user_id == user.id,
                Models.AttendancePunchInOutModule.status == "active",
            )
            .first()
        )

        if not active_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.NO_ACTIVE_ATTENDANCE_SESSION,
                    "success": SUCCESS.FALSE,
                },
            )

        location_query_data = (
            db.query(Models.OrganizationLocationsConfig)
            .filter(Models.OrganizationLocationsConfig.organization_id == user.organization_id)
            .all()
        )

        if not location_query_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.NO_LOCATION_CONFIG_ADDED,
                    "error": str(e),
                    "success": SUCCESS.FALSE,
                },
            )

        is_with_in_range = False

        for location_config in location_query_data:

            user_location_coordinates = {
                "latitude": (
                    data.location_coordinates.get("latitude")
                    if isinstance(data.location_coordinates, dict)
                    else data.location_coordinates.latitude
                ),
                "longitude": (
                    data.location_coordinates.get("longitude")
                    if isinstance(data.location_coordinates, dict)
                    else data.location_coordinates.longitude
                ),
            }

            org_location_coordinates = json.loads(location_config.location_coordinates)

            allowed_radius_meters = (
                location_config.allowed_radius_meters
                if location_config.allowed_radius_meters
                else 500
            )

            distance = calculateDistanceWithHaversine(
                userLocation={
                    "latitude": user_location_coordinates["latitude"],
                    "longitude": user_location_coordinates["longitude"],
                },
                orgLocation={
                    "latitude": org_location_coordinates["latitude"],
                    "longitude": org_location_coordinates["longitude"],
                },
            )

            if distance <= allowed_radius_meters:
                is_with_in_range = True
                break
            else:
                continue

        if is_with_in_range:

            break_data = (
                db.query(Models.AttendanceBreakModel)
                .filter(
                    Models.AttendanceBreakModel.session_id == active_session.id,
                    Models.AttendanceBreakModel.status == "active",
                )
                .first()
            )

            punch_in_coords = (
                json.loads(break_data.punch_in_coordinates)
                if break_data.punch_in_coordinates
                else None
            )

            is_mislinious: bool = False

            if punch_in_coords:

                distance = calculateDistanceWithHaversine(
                    userLocation={
                        "latitude": punch_in_coords["latitude"],
                        "longitude": punch_in_coords["longitude"],
                    },
                    orgLocation={
                        "latitude": data.location_coordinates.latitude,
                        "longitude": data.location_coordinates.longitude,
                    },
                )

                if distance > 1000:
                    is_mislinious = True
                else:
                    is_mislinious = False
            else:
                is_mislinious = True

            break_start_time = break_data.break_start_time
            if isinstance(break_data.break_start_time, str):
                break_start_time = datetime.fromisoformat(break_data.break_start_time)

            break_data.break_end_time = datetime.utcnow()
            break_data.break_duration = (
                break_data.break_end_time - break_start_time
            ).total_seconds() / 60
            break_data.punch_out_coordinates = json.dumps(data.location_coordinates.model_dump())
            break_data.is_mislinious = is_mislinious
            break_data.status = "completed"

            db.commit()

            return {
                "message": SUCCESS_MESSAGE.BREAK_ENDED_SUCCESSFULLY,
                "success": SUCCESS.TRUE,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.OUT_OF_RANGE_ATTENDANCE_PUNCH,
                    "success": SUCCESS.FALSE,
                },
            )

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_FETCHING_ATTENDANCE_STATUS,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.post("/punch-out", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def AttendancePunchOut(
    request: Request,
    db: db_dependencies,
    data: AttendancePunchInPydantic,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        active_session = (
            db.query(Models.AttendancePunchInOutModule)
            .filter(
                Models.AttendancePunchInOutModule.user_id == user.id,
                Models.AttendancePunchInOutModule.status == "active",
            )
            .first()
        )

        if not active_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.NO_ACTIVE_ATTENDANCE_SESSION,
                    "success": SUCCESS.FALSE,
                },
            )
        query_data = (
            db.query(Models.OrganizationLocationsConfig)
            .filter(Models.OrganizationLocationsConfig.organization_id == user.organization_id)
            .all()
        )

        if not query_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.NO_LOCATION_CONFIG_ADDED,
                    "error": str(e),
                    "success": SUCCESS.FALSE,
                },
            )
        is_with_in_range = False

        break_data = (
            db.query(Models.AttendanceBreakModel)
            .filter(
                Models.AttendanceBreakModel.session_id == active_session.id,
                Models.AttendanceBreakModel.status == "active",
            )
            .first()
        )

        if break_data:
            break_start_time = break_data.break_start_time
            if isinstance(break_data.break_start_time, str):
                break_start_time = datetime.fromisoformat(break_data.break_start_time)

            break_data.break_end_time = datetime.utcnow()
            break_data.break_duration = (
                break_data.break_end_time - break_start_time
            ).total_seconds()
            break_data.punch_out_coordinates = json.dumps(data.location_coordinates.model_dump())
            break_data.is_mislinious = False
            break_data.status = "completed"

        if not data.is_work_from_home:
            for location_config in query_data:

                user_location_coordinates = {
                    "latitude": (
                        data.location_coordinates.get("latitude")
                        if isinstance(data.location_coordinates, dict)
                        else data.location_coordinates.latitude
                    ),
                    "longitude": (
                        data.location_coordinates.get("longitude")
                        if isinstance(data.location_coordinates, dict)
                        else data.location_coordinates.longitude
                    ),
                }

                org_location_coordinates = json.loads(location_config.location_coordinates)

                allowed_radius_meters = (
                    location_config.allowed_radius_meters
                    if location_config.allowed_radius_meters
                    else 500
                )

                distance = calculateDistanceWithHaversine(
                    userLocation={
                        "latitude": user_location_coordinates["latitude"],
                        "longitude": user_location_coordinates["longitude"],
                    },
                    orgLocation={
                        "latitude": org_location_coordinates["latitude"],
                        "longitude": org_location_coordinates["longitude"],
                    },
                )

                if distance <= allowed_radius_meters:
                    is_with_in_range = True
                    break
                else:
                    continue

            if is_with_in_range:

                punch_in_coords = (
                    json.loads(active_session.punch_in_coordinates)
                    if active_session.punch_in_coordinates
                    else None
                )

                is_mislinious: bool = False

                if punch_in_coords:

                    distance = calculateDistanceWithHaversine(
                        userLocation={
                            "latitude": punch_in_coords["latitude"],
                            "longitude": punch_in_coords["longitude"],
                        },
                        orgLocation={
                            "latitude": data.location_coordinates.latitude,
                            "longitude": data.location_coordinates.longitude,
                        },
                    )

                    if distance > 1000:
                        is_mislinious = True
                    else:
                        is_mislinious = False
                else:
                    is_mislinious = True

                active_session.punch_out_time = datetime.utcnow()
                active_session.punch_out_coordinates = json.dumps(
                    data.location_coordinates.model_dump()
                )
                active_session.status = "completed"
                active_session.is_mislinious = is_mislinious

                punch_in_time = active_session.punch_in_time
                if isinstance(active_session.punch_in_time, str):
                    punch_in_time = datetime.fromisoformat(active_session.punch_in_time)

                punch_out_time = active_session.punch_out_time
                if isinstance(active_session.punch_out_time, str):
                    punch_out_time = datetime.fromisoformat(active_session.punch_out_time)

                gross_seconds = (punch_out_time - punch_in_time).total_seconds()
                gross_hours = gross_seconds / 3600

                total_break_minutes = sum(
                    [b.break_duration or 0 for b in active_session.attendance_breaks]
                )

                total_break_hours = total_break_minutes / 60

                total_working_hours = max(0, gross_hours - total_break_hours)
                active_session.gross_hours = round(gross_hours, 2)
                active_session.total_break_hours = round(total_break_hours, 2)
                active_session.total_working_hours = round(total_working_hours, 2)

                db.commit()
                db.refresh(active_session)

                return {
                    "message": SUCCESS_MESSAGE.ATTENDANCE_PUNCH_IN_SUCCESSFULLY,
                    "success": SUCCESS.TRUE,
                }

        else:
            active_session.punch_out_time = datetime.utcnow()
            active_session.punch_out_coordinates = json.dumps(
                data.location_coordinates.model_dump()
            )
            active_session.status = "completed"
            active_session.is_mislinious = False

            punch_in_time = active_session.punch_in_time
            if isinstance(active_session.punch_in_time, str):
                punch_in_time = datetime.fromisoformat(active_session.punch_in_time)

            punch_out_time = active_session.punch_out_time
            if isinstance(active_session.punch_out_time, str):
                punch_out_time = datetime.fromisoformat(active_session.punch_out_time)

            gross_seconds = (punch_out_time - punch_in_time).total_seconds()
            gross_hours = gross_seconds / 3600

            total_break_minutes = sum(
                [b.break_duration or 0 for b in active_session.attendance_breaks]
            )

            total_break_hours = total_break_minutes / 60

            total_working_hours = max(0, gross_hours - total_break_hours)
            active_session.gross_hours = round(gross_hours, 2)
            active_session.total_break_hours = round(total_break_hours, 2)
            active_session.total_working_hours = round(total_working_hours, 2)

            db.commit()
            db.refresh(active_session)

            return {
                "message": SUCCESS_MESSAGE.ATTENDANCE_PUNCH_IN_SUCCESSFULLY,
                "success": SUCCESS.TRUE,
            }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_APPLYING_LEAVE,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


# leave_data = [
#     {
#         "start_date": "2026-03-12",
#         "end_date": "2026-03-14",
#         "start_half": "second_half",
#         "end_half": "second_half",
#         "leave_name": "Annual Leave test one",
#         "leave_code": "ALV-TEST",
#         "status": "rejected",
#         "total_days": 2.5,
#         "description": "sada",
#         "documents": "[]",
#         "created_at": "2026-03-12T09:53:20",
#         "updated_at": "2026-03-12T10:13:11",
#         "created_by": '{"first_name": "super", "last_name": "admin"}',
#     }
# ]


# @attendanceRoute.get("/export/leaves/csv")
# async def export_leaves_csv():

#     df = pd.DataFrame(leave_data)

#     file_path = "leaves_export.csv"
#     df.to_csv(file_path, index=False)

#     return FileResponse(file_path, media_type="text/csv", filename="leaves_export.csv")


# @attendanceRoute.get("/export/leaves/pdf")
# async def export_leaves_pdf():

#     file_path = "leaves_export.pdf"

#     styles = getSampleStyleSheet()

#     elements = []

#     title = Paragraph("Leave Report", styles["Title"])
#     elements.append(title)

#     table_data = [
#         [
#             "Leave Name",
#             "Leave Code",
#             "Start Date",
#             "End Date",
#             "Start Half",
#             "End Half",
#             "Total Days",
#             "Status",
#         ]
#     ]

#     for leave in leave_data:
#         table_data.append(
#             [
#                 leave["leave_name"],
#                 leave["leave_code"],
#                 leave["start_date"],
#                 leave["end_date"],
#                 leave["start_half"],
#                 leave["end_half"],
#                 leave["total_days"],
#                 leave["status"],
#             ]
#         )

#     table = Table(table_data)

#     table.setStyle(
#         TableStyle(
#             [
#                 ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
#                 ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
#                 ("ALIGN", (0, 0), (-1, -1), "CENTER"),
#                 ("GRID", (0, 0), (-1, -1), 1, colors.black),
#             ]
#         )
#     )

#     elements.append(table)

#     doc = SimpleDocTemplate(file_path, pagesize=A4)
#     doc.build(elements)

#     return FileResponse(file_path, media_type="application/pdf", filename="leaves_export.pdf")
