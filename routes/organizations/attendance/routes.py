from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status

from config.EnvConfig import EnvConfig
from constants.constant import SUCCESS
from database.Database import db_dependencies
from middleware.RateLimiting import limiter
from middleware.UserAuthenticator import UserAuthenticatorMiddleware
from models.pydantic.Organizations.AttendancePydanticModal import (
    ApplyLeavePydanticModel,
    AttendancePunchInPydantic,
    fetchAppliedLeavesQueryPydanticModel,
    fetchAppliedOrganizationLeave,
    updateLeavesQueryPydanticModel,
)
from routes.organizations.attendance.session import service as sessionController
from utils.responseMessages import ERROR_MESSAGE

from .dependencies import (
    get_apply_leave_dependencies,
    get_fetch_leaves_dependencies,
    get_organization_fetch_leaves_dependencies,
    update_leave_request_dependencies,
)
from .leave import service as leaveController

API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING

attendanceRoute = APIRouter(prefix="/app/v1/attendance", tags=["Attendance"])


# This is the api route that is used for applying the leave
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
        return await leaveController.handle_apply_leave_service_function(
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
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ERROR_WHILE_APPLYING_LEAVE,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


# This is the route that is used for fetching all the leaves For the user
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
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ERROR_WHILE_FETCHING_EMP_LEAVE,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


# This is the api in which we will fetch the leaves for the organization
@attendanceRoute.get(path="/leaves/organization/fetch-all", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_all_leaves_of_organization(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    query_data: fetchAppliedOrganizationLeave = Depends(get_organization_fetch_leaves_dependencies),
):
    try:
        return await leaveController.fetch_organization_leaves(db=db, user=user, query_data=query_data)
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ERROR_WHILE_FETCHING_ORGANIZATION_LEAVES,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


# This is the api in which we will fetch the leaves balance
@attendanceRoute.get(path="/leaves/balance/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_employee_leaves_balance(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    employee_id: Optional[str] = Query(None, alias="employee-id"),
):
    try:
        return await leaveController.fetch_employee_leaves_balance_service(db=db, user=user, employee_id=employee_id)
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ERROR_WHILE_FETCHING_LEAVES_BALANCE,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


# This is the api in which we are fetching the leaves of the employee whose reporting manager are you
@attendanceRoute.get(path="/leaves/team/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_team_member_leaves(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    query_data: fetchAppliedLeavesQueryPydanticModel = Depends(get_fetch_leaves_dependencies),
):
    try:
        return await leaveController.fetch_team_member_leaves_service(db=db, user=user, query_data=query_data)
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ERROR_WHILE_FETCHING_TEAM_MEMBER_LEAVES,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.get(path="/leaves/organization/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_team_member_leaves(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    query_data: fetchAppliedLeavesQueryPydanticModel = Depends(get_fetch_leaves_dependencies),
):
    try:
        return await leaveController.fetch_organization_leaves_service(db=db, user=user, query_data=query_data)
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ERROR_WHILE_FETCHING_ORGANIZATION_EMPLOYEE_LEAVES,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


""" We have to add the Process in which we will update the leave request if the users permission have that """


@attendanceRoute.put(path="/leaves/request/update", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def update_leave_request_update(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    query_data: updateLeavesQueryPydanticModel = Depends(update_leave_request_dependencies),
):
    try:
        return await leaveController.update_leave_request_service_function(db=db, user=user, query_data=query_data)
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ERROR_WHILE_FETCHING_LEAVE_TYPES,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.get(path="/leaves/types/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_leaves_types(request: Request, db: db_dependencies, user: dict = Depends(UserAuthenticatorMiddleware)):
    try:
        return await leaveController.fetch_leaves_type_service(
            db=db,
            user=user,
        )
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ERROR_WHILE_UPDATING_LEAVES,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.post(path="/session/punch-in", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def attendance_session_punch_in(
    request: Request,
    db: db_dependencies,
    data: AttendancePunchInPydantic,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        return await sessionController.attendance_session_punch_in_service_function(db=db, data=data, user=user)
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ERROR_WHILE_PUNCHING_IN,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.get(path="/session/attendance-status", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def attendance_session_punch_in(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        return await sessionController.attendance_session_get_status_service_function(db=db, user=user)
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ERROR_WHILE_FETCHING_ATTENDANCE_STATUS,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.get(path="/session/punch-in-out/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_attendance_punch_in_out_details(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    month: int | None = Query(None, ge=1, le=12),
    year: int | None = Query(None),
):
    try:
        return await sessionController.fetch_punch_in_punch_out_status(db=db, user=user, month=month, year=year)
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ERROR_WHILE_FETCHING_ATTENDANCE_STATUS,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.post(path="/session/break/start-break", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def attendance_sessions_breaks_start_a_break(
    request: Request,
    db: db_dependencies,
    data: AttendancePunchInPydantic,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        return await sessionController.attendance_sessions_breaks_start_a_break_service_function(
            db=db, user=user, data=data
        )
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ERROR_WHILE_FETCHING_ATTENDANCE_STATUS,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.post(path="/session/break/end-break", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def attendance_sessions_breaks_end_a_break(
    request: Request,
    db: db_dependencies,
    data: AttendancePunchInPydantic,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        return await sessionController.attendance_sessions_breaks_end_a_break_service_function(
            db=db, user=user, data=data
        )
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ERROR_WHILE_FETCHING_ATTENDANCE_STATUS,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@attendanceRoute.post(path="/session/punch-out", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def attendance_sessions_breaks_end_a_break(
    request: Request,
    db: db_dependencies,
    data: AttendancePunchInPydantic,
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        return await sessionController.attendance_session_punch_out_service_function(db=db, user=user, data=data)
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ERROR_WHILE_FETCHING_ATTENDANCE_STATUS,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )
