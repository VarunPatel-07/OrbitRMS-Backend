from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status

from config.EnvConfig import EnvConfig
from constants.constant import SUCCESS
from database.Database import db_dependencies
from middleware.RateLimiting import limiter
from middleware.UserAuthenticator import UserAuthenticatorMiddleware
from models.pydantic.Organizations.AttendancePydanticModal import (
    ApplyLeavePydanticModel,
    fetchAppliedLeavesQueryPydanticModel,
)
from utils.responseMessages import ERROR_MESSAGE

from .dependencies import get_apply_leave_dependencies, get_fetch_leaves_dependencies
from .leave import service as leaveController

API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING

attendanceRoute = APIRouter(prefix="/app/v1/attendance", tags=["Attendance"])


@attendanceRoute.post("/leave/apply", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def handle_apply_leave(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    data: ApplyLeavePydanticModel = Depends(get_apply_leave_dependencies),
    documents: Optional[List[UploadFile]] = File(None),
    employee_id: Optional[str] = Query(None, alias="employee-id"),
):
    try:
        return await leaveController.handle_apply_leave(
            db,
            user,
            data,
            documents,
            employee_id,
        )
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


@attendanceRoute.get("/leave/fetch-all", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_all_leaves(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    query_data: fetchAppliedLeavesQueryPydanticModel = Depends(get_fetch_leaves_dependencies),
):
    try:
        return await leaveController.fetch_user_leaves(
            db,
            user,
            query_data,
        )
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


