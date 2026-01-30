import concurrent.futures
import json
import math
from datetime import date
from typing import List, Optional
import uuid
import cloudinary
import cloudinary.uploader
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
from utils.helper.helper import parse_to_utc_date
from sqlalchemy import and_
from constants.constant import SUCCESS
from config.EnvConfig import EnvConfig
from database.Database import db_dependencies
from middleware.UserAuthenticator import UserAuthenticatorMiddleware
from models.sql import Models
from middleware.RateLimiting import limiter
from utils.helper.helper import filter_fields
from utils.helper.helper import model_to_filtered_dict
from utils.responseMessages import ERROR_MESSAGE, SUCCESS_MESSAGE

attendanceRoute = APIRouter(prefix="/app/v1/attendance", tags=["Attendance"])

API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING


cloudinary.config(
    cloud_name=EnvConfig.CLOUDINARY_CLOUD_NAME,
    api_key=EnvConfig.CLOUDINARY_API_KEY,
    api_secret=EnvConfig.CLOUDINARY_API_SECRET,
)


def upload_pdf_function(document):
    result = cloudinary.uploader.upload(document)

    return result["secure_url"]


@attendanceRoute.post("/apply/leave", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def handel_apply_ratelimiting(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    # employee_id: str = Optional[Query(None, alias="employee-id")],
    leave_type_id: str = Form(...),
    start_date: str = Form(...),
    start_half: str = Form(...),
    end_date: str = Form(...),
    end_half: str = Form(...),
    current_date: str = Form(...),
    description: str = Form(None),
    notify_to: Optional[str] = Form(None),
    documents: Optional[List[UploadFile]] = File(None),
):
    try:

        start_date_utc = parse_to_utc_date(start_date)
        end_date_utc = parse_to_utc_date(end_date)
        current_date_utc = parse_to_utc_date(current_date)

        # print("start_date_utc", start_date_utc)
        # print("end_date_utc", end_date_utc)
        # print("current_date_utc", current_date_utc)

        query_id = user.id
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
                Models.LeaveBalance.user_id == user.id,
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
            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = list(executor.map(upload_pdf_function, documents))

            uploaded_documents += result

        notify_to_users_array = []

        if notify_to:
            employee_array = json.loads(notify_to)
            for employee in employee_array:
                user_info = (
                    db.query(Models.User)
                    .filter(Models.User.id == employee.get("employee_id"))
                    .first()
                )

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


@attendanceRoute.get("/fetch/leaves", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_users_leave(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    page: int = Query(..., alias="page"),
    limit: int = Query(..., alias="limit"),
):
    try:
        query_data = db.query(Models.User).filter(Models.User.id == user.id).first()
        _data = [data for data in query_data.applied_leaves]

        total_data = len(_data)
        page = page if page else 1
        limit = limit if limit else 10
        start = (page - 1) * limit
        end = start + limit
        query_data = _data[start:end]

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
):
    try:
        query_data = (
            db.query(Models.LeaveBalance).filter(Models.LeaveBalance.user_id == user.id).all()
        )

        data = []

        for _data in query_data:
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
