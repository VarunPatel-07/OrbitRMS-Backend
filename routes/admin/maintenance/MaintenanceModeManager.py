import json
import math
import os
from datetime import datetime
from typing import Optional
from urllib.parse import unquote
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import joinedload
from constants.constant import SUCCESS
from config.EnvConfig import EnvConfig
from database.Database import db_dependencies
from middleware.verifyToken import verify_token
from models.pydantic.Admin.AdminAuthenticationModel import (
    MaintenanceModeData,
    MaintenanceModeMessageData,
    ScheduleMaintenanceModeCancellationData,
    ScheduleMaintenanceModeData,
)
from models.sql import Models
from middleware.RateLimiting import limiter
from utils.helper.helper import (
    model_to_filtered_dict,
    parse_date,
    parse_iso_datetime,
    validate_time_difference,
)
from utils.responseMessages import ERROR_MESSAGE, SUCCESS_MESSAGE

from .MaintenanceModeQueryFilter import MaintenanceModeQueryFilter

load_dotenv(override=True)

API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING


MaintenanceMode = APIRouter(prefix="/app/v1/admin/maintenance-mode")


@MaintenanceMode.put("/manual/toggle", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Toggle_Maintenance_Mode(
    request: Request,
    db: db_dependencies,
    maintenance_mode_data: MaintenanceModeData,
    token: str = Depends(verify_token),
    type: str = Query(..., alias="type"),
):
    try:
        if type not in ["activate", "deactivate"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Invalid type. Only 'activate' or 'deactivate' are allowed.",
                    "success": SUCCESS.FALSE,
                },
            )
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized", "success": SUCCESS.FAlSE},
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
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid session", "success": SUCCESS.FAlSE},
            )
        maintenance_mode = db.query(Models.MaintenanceMode).first()

        if type == "activate":
            maintenance_logs = (
                db.query(Models.MaintenanceLog)
                .filter(Models.MaintenanceLog.status == "active")
                .all()
            )

            if maintenance_logs:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "A maintenance session is already in progress. Please complete it before starting another.",
                        "success": SUCCESS.FALSE,
                    },
                )

        if maintenance_mode:

            if not maintenance_mode.is_active:
                maintenance_mode.is_active = True
                maintenance_mode.updated_by = "Orbit Admin"
                maintenance_mode.message = maintenance_mode_data.message

                started_at = datetime.now(ZoneInfo("UTC"))
                print(started_at)

                db.add(
                    Models.MaintenanceLog(
                        started_at=started_at,
                        ended_at=None,
                        started_by="Orbit Admin",
                        ended_by="",
                        type="manual",
                        status="active",
                        reason=maintenance_mode_data.reason,
                        message=maintenance_mode_data.message,
                        maintenance_mode_id=maintenance_mode.id,
                    )
                )

                db.commit()
                db.refresh(maintenance_mode)
                return {
                    "message": "Maintenance Mode Is Now Active",
                    "success": SUCCESS.TRUE,
                    "data": maintenance_mode,
                }

            else:
                maintenance_mode.is_active = False
                db.commit()
                db.refresh(maintenance_mode)
                maintenance_log = (
                    db.query(Models.MaintenanceLog)
                    .filter(
                        Models.MaintenanceLog.status == "active",
                    )
                    .first()
                )

                ended_at = datetime.now(ZoneInfo("UTC"))

                maintenance_log.status = "completed"
                maintenance_log.ended_by = "Orbit Admin"
                maintenance_log.ended_at = ended_at

                db.commit()
                db.refresh(maintenance_log)
                return {
                    "message": "Maintenance Mode Is Deactivated",
                    "success": SUCCESS.TRUE,
                    "data": maintenance_mode,
                }

        return {
            "message": "Maintenance Dose Not Exist",
            "success": SUCCESS.FAlSE,
            "data": maintenance_mode,
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while toggling Maintenance Mode",
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@MaintenanceMode.put("/schedule/setup", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Maintenance_Mode_Schedule_Toggler(
    request: Request,
    db: db_dependencies,
    maintenance_mode_data: ScheduleMaintenanceModeData,
    token: str = Depends(verify_token),
):
    try:
        if len(maintenance_mode_data.reason) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "The Reason Is An Required Field", "success": SUCCESS.FAlSE},
            )
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized", "success": SUCCESS.FAlSE},
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
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid session", "success": SUCCESS.FAlSE},
            )
        maintenance_mode = db.query(Models.MaintenanceMode).first()

        start_date = parse_date(maintenance_mode_data.started_at)
        end_date = parse_date(maintenance_mode_data.ended_at)

        print("start_date", start_date)

        print("end_date", end_date)

        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Enter Valid Date Difference",
                    "success": SUCCESS.FALSE,
                },
            )

        if (
            validate_time_difference(
                maintenance_mode_data.started_at, maintenance_mode_data.ended_at
            )
            <= 30
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Start and end time must be at least 30 minutes apart.",
                    "success": SUCCESS.FALSE,
                },
            )

        maintenance_logs = (
            db.query(Models.MaintenanceLog).filter(Models.MaintenanceLog.status == "active").all()
        )

        if maintenance_logs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "A maintenance session is already in progress. Please complete it before starting another.",
                    "success": SUCCESS.FALSE,
                },
            )

        if maintenance_mode:

            db.add(
                Models.MaintenanceLog(
                    started_at=parse_iso_datetime(maintenance_mode_data.started_at),
                    ended_at=parse_iso_datetime(maintenance_mode_data.ended_at),
                    started_by="Orbit Admin",
                    ended_by="Orbit Admin",
                    type="scheduled",
                    status="scheduled",
                    reason=maintenance_mode_data.reason,
                    message=maintenance_mode_data.message,
                    maintenance_mode_id=maintenance_mode.id,
                )
            )

            db.commit()
            db.refresh(maintenance_mode)
            return {
                "message": "Maintenance Mode Is Now Scheduled",
                "success": SUCCESS.TRUE,
                "data": maintenance_mode,
            }

        return {
            "message": "Maintenance Dose Not Exist",
            "success": SUCCESS.FAlSE,
            "data": maintenance_mode,
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while toggling Maintenance Mode",
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@MaintenanceMode.get("/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Toggle_Maintenance_Mode(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized", "success": SUCCESS.FAlSE},
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
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid session", "success": SUCCESS.FAlSE},
            )

        maintenance_mode = db.query(Models.MaintenanceMode).first()

        maintenance_logs = (
            db.query(Models.MaintenanceLog)
            .filter(Models.MaintenanceLog.status.in_(["active", "scheduled"]))
            .first()
        )

        return {
            "message": "Maintenance Mode info Fetched Successfully",
            "success": SUCCESS.TRUE,
            "data": {
                **model_to_filtered_dict(maintenance_mode),
                "status": maintenance_logs.status if maintenance_logs else "inActive",
                "scheduler_info": (
                    {
                        "started_at": maintenance_logs.started_at,
                        "started_by": maintenance_logs.started_by,
                        "ended_at": maintenance_logs.ended_at,
                        "ended_by": maintenance_logs.ended_by,
                        "id": maintenance_logs.id,
                    }
                    if maintenance_logs
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
                "message": "error while toggling Maintenance Mode",
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@MaintenanceMode.get("/history/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Fetch_ALL_Maintenance_Mode_History(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    page: int = Query(..., alias="page"),
    limit: int = Query(..., alias="limit"),
    filter: Optional[str] = Query(None),
    order: str = Query("desc", alias="order"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized", "success": SUCCESS.FAlSE},
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
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid session", "success": SUCCESS.FAlSE},
            )

        filter_data: str = ""

        if filter:
            decoded = unquote(filter)
            filter_data = json.loads(decoded)

        query_data = db.query(Models.MaintenanceLog)
        if not query_data:
            return {
                "message": "No Maintenance Logs Found",
                "data": [],
                "success": SUCCESS.TRUE,
            }

        if filter_data:
            query_data = MaintenanceModeQueryFilter(query_data, filter_data)

        total_data = query_data.count()
        page = page if page else 1
        limit = limit if limit else 10
        start = (page - 1) * limit
        end = start + limit
        query_data = query_data.offset(start).limit(end)

        maintenance_logs = query_data.all()

        maintenance_logs = sorted(
            maintenance_logs, key=lambda x: x.created_at, reverse=(order.lower() == "desc")
        )

        return {
            "message": "Organizations fetched successfully",
            "success": SUCCESS.TRUE,
            "data": maintenance_logs if maintenance_logs else [],
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
                "message": "error while toggling Maintenance Mode",
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@MaintenanceMode.put("/schedule/edit", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Edit_Scheduler_Info(
    request: Request,
    db: db_dependencies,
    maintenance_mode_data: ScheduleMaintenanceModeData,
    token: str = Depends(verify_token),
    id: str = Query(..., alias="id"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized", "success": SUCCESS.FAlSE},
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
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid session", "success": SUCCESS.FAlSE},
            )

        maintenance_log = (
            db.query(Models.MaintenanceLog).filter(Models.MaintenanceLog.id == id).first()
        )

        if not maintenance_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "No Such Maintenance Log Found", "success": SUCCESS.FAlSE},
            )

        if (
            validate_time_difference(
                maintenance_mode_data.started_at, maintenance_mode_data.ended_at
            )
            <= 30
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Start and end time must be at least 30 minutes apart.",
                    "success": SUCCESS.FALSE,
                },
            )

        maintenance_log.started_at = parse_iso_datetime(maintenance_mode_data.started_at)
        maintenance_log.ended_at = parse_iso_datetime(maintenance_mode_data.ended_at)
        maintenance_log.reason = maintenance_mode_data.reason

        db.commit()

        return {
            "message": "scheduler Updated Successfully",
            "success": SUCCESS.TRUE,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while toggling Maintenance Mode",
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@MaintenanceMode.put("/schedule/cancellation", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Edit_Scheduler_Info(
    request: Request,
    db: db_dependencies,
    maintenance_mode_data: ScheduleMaintenanceModeCancellationData,
    token: str = Depends(verify_token),
    id: str = Query(..., alias="id"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized", "success": SUCCESS.FAlSE},
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
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid session", "success": SUCCESS.FAlSE},
            )

        maintenance_log = (
            db.query(Models.MaintenanceLog).filter(Models.MaintenanceLog.id == id).first()
        )

        if not maintenance_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "No Such Maintenance Log Found", "success": SUCCESS.FAlSE},
            )

        maintenance_log.cancellation_reason = maintenance_mode_data.reason

        maintenance_log.status = "cancelled"

        db.commit()

        return {
            "message": "scheduler Updated Successfully",
            "success": SUCCESS.TRUE,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while toggling Maintenance Mode",
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@MaintenanceMode.put("/edit/save-message", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Save_Message(
    request: Request,
    db: db_dependencies,
    maintenance_mode_data: MaintenanceModeMessageData,
    token: str = Depends(verify_token),
    id: str = Query(..., alias="id"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized", "success": SUCCESS.FAlSE},
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
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid session", "success": SUCCESS.FAlSE},
            )

        maintenance_mode = (
            db.query(Models.MaintenanceMode).filter(Models.MaintenanceMode.id == id).first()
        )

        if not maintenance_mode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "No Such Maintenance Mode Found", "success": SUCCESS.FAlSE},
            )

        maintenance_mode.message = maintenance_mode_data.message

        db.commit()

        return {
            "message": "Message Updated Successfully",
            "success": SUCCESS.TRUE,
            "data": {"message": maintenance_mode.message},
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while toggling Maintenance Mode",
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )
