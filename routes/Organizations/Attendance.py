import concurrent.futures
import json
import math
from datetime import date
from typing import List, Optional

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
from sqlalchemy import and_

from Config.EnvConfig import EnvConfig
from Database.Database import db_dependencies
from Helper.createModelInstance import cerate_model_instance
from Helper.helper import model_to_filtered_dict
from Middleware.UserAuthenticator import UserAuthenticatorMiddleware
from RateLimiting import limiter
from SqlModels import Models

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
    employee_id: str = Query(..., alias="employee-id"),
    leave_type: str = Form(...),
    start_date: date = Form(...),
    start_half: str = Form(...),
    end_date: date = Form(...),
    end_half: str = Form(...),
    current_date: date = Form(...),
    description: str = Form(None),
    notify_to: Optional[str] = Form(None),
    documents: Optional[List[UploadFile]] = File(None),
):
    try:
        employee_info = db.query(Models.User).filter(Models.User.id == employee_id).first()

        if not employee_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User Not Found",
                    "success": False,
                },
            )

        updated_created_by_user = model_to_filtered_dict(
            user.personal_info, ["user_id", "first_name", "last_name"]
        )

        difference_btw_date = (start_date - current_date).days
        is_planned = difference_btw_date > 5

        total_days = (end_date - start_date).days

        if total_days == 0:
            if start_half == "first_half" and end_half == "first_half":
                total_days = 0.5
            elif start_half == "second_half" and end_half == "second_half":
                total_days = 0.5
            else:
                total_days = 1
        else:
            total_days = total_days + 1
            if start_half == "second_half":
                total_days -= 0.5
            elif end_half == "first_half":
                total_days -= 0.5

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

            notify_to_users_array.append(user_info)

        leave_info = Models.AttendanceLeavesModule(
            leave_type=leave_type,
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
            user_id=employee_id,
            created_by=json.dumps(updated_created_by_user),
        )

        db.add(leave_info)
        db.commit()

        return {
            "message": "Leave Added Successfully",
            "success": True,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while Fetching The User Info",
                "error": str(e),
                "success": False,
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
            "message": "user verified successfully",
            "success": True,
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
                "message": "error while Fetching Leaves",
                "error": str(e),
                "success": False,
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
            "message": "All Leaves Fetched Successfully",
            "success": True,
            "data": users_data,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while Fetching The User Info",
                "error": str(e),
                "success": False,
            },
        )
