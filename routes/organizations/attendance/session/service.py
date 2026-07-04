from datetime import date, datetime, timedelta
import json


from constants.constant import SUCCESS
from middleware.UserAuthenticator import UserAuthenticatorMiddleware
from models.pydantic.Organizations.AttendancePydanticModal import AttendancePunchInPydantic
from routes.organizations.attendance.session import crude as crudeController
from database.Database import db_dependencies
from routes.organizations.attendance.session import utils
from utils.helper.helper import model_to_filtered_dict
from utils.responseMessages import ERROR_MESSAGE, SUCCESS_MESSAGE
from fastapi import Depends, status, HTTPException, Query


async def attendance_session_punch_in_service_function(
    db: db_dependencies, data: AttendancePunchInPydantic, user: dict
):
    active_session = await crudeController.fetch_attendance_active_sessions_crude_service(db=db, user_id=user.id)

    if active_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ACTIVE_ATTENDANCE_SESSION_FOUND,
                "success": SUCCESS.FALSE,
            },
        )

    today_start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end_date = today_start_date + timedelta(days=1)

    active_today_session = await crudeController.fetch_today_sessions_crude_service(
        db=db, user_id=user.id, today_start_date=today_start_date, today_end_date=today_end_date
    )

    if active_today_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ACTIVE_SESSION_FOR_TODAY,
                "success": SUCCESS.FALSE,
            },
        )

    org_location_config_data = await crudeController.fetch_org_location_config_crude_service(
        db=db, organization_id=user.organization_id
    )

    if not org_location_config_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.NO_LOCATION_CONFIG_ADDED,
                "success": SUCCESS.FALSE,
            },
        )

    if not data.is_work_from_home:

        is_with_in_range = utils.calculate_org_emp_location_boundary(
            data=data, org_location_config_data=org_location_config_data
        )

        if is_with_in_range:
            attendance_data = await crudeController.add_attendance_punch_in_punch_out(db=db, data=data, user_id=user.id)

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
                    "message": ERROR_MESSAGE.ATTENDANCE_MODULE.OUT_OF_RANGE_ATTENDANCE_PUNCH,
                    "success": SUCCESS.FALSE,
                },
            )

    else:
        attendance_data = await crudeController.add_attendance_punch_in_punch_out(db=db, data=data, user_id=user.id)

        return {
            "message": SUCCESS_MESSAGE.ATTENDANCE_PUNCH_IN_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": {
                "attendance_id": attendance_data.id,
                "punch_in_time": attendance_data.punch_in_time,
            },
        }


async def attendance_session_get_status_service_function(db: db_dependencies, user: dict):

    active_session = await crudeController.fetch_attendance_active_sessions_crude_service(db=db, user_id=user.id)

    if not active_session:
        last_session = await crudeController.get_last_session_details_crude_service(db=db, user_id=user.id)

        if not last_session:
            return {
                "message": SUCCESS_MESSAGE.NO_ACTIVE_ATTENDANCE_SESSION,
                "success": SUCCESS.TRUE,
            }

        return utils.formate_last_session_data(last_session=last_session)

    return utils.formate_active_session_data(active_session=active_session)


async def fetch_punch_in_punch_out_status(
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    month: int | None = Query(None, ge=1, le=12),
    year: int | None = Query(None),
):
    current_date = datetime.utcnow()
    target_year = year if year else current_date.year
    target_month = month if month else current_date.month

    start_of_month = datetime(target_year, target_month, 1)

    # handle December edge case
    if target_month == 12:
        end_of_month = datetime(target_year + 1, 1, 1)
    else:
        end_of_month = datetime(target_year, target_month + 1, 1)

    monthly_data = await crudeController.fetch_attendance_punch_in_out_status(
        db=db, user_id=user.id, start_of_month=start_of_month, end_of_month=end_of_month
    )

    return {
        "message": SUCCESS_MESSAGE.ATTENDANCE_SESSION_ACTIVE,
        "success": SUCCESS.TRUE,
        "data": [
            {
                **model_to_filtered_dict(session, ["-attendance_breaks"]),
                "breaks": [
                    {**model_to_filtered_dict(attendance_break)} for attendance_break in session.attendance_breaks
                ],
            }
            for session in monthly_data
            if session is not None
        ],
    }


async def attendance_sessions_breaks_start_a_break_service_function(
    db: db_dependencies, data: AttendancePunchInPydantic, user: dict
):
    active_session = await crudeController.fetch_attendance_active_sessions_crude_service(db=db, user_id=user.id)

    if not active_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.NO_ACTIVE_ATTENDANCE_SESSION,
                "success": SUCCESS.FALSE,
            },
        )

    active_break = await crudeController.fetch_attendance_active_break_crude_service(
        db=db, active_session_id=active_session.id
    )

    if active_break:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.CANT_ACTIVE_BECAUSE_ACTIVE_BREAK_FOUND,
                "success": SUCCESS.FALSE,
            },
        )

    org_location_config_data = await crudeController.fetch_org_location_config_crude_service(
        db=db, organization_id=user.organization_id
    )

    if not data.is_work_from_home:

        is_with_in_range = utils.calculate_org_emp_location_boundary(
            data=data, org_location_config_data=org_location_config_data
        )

        if is_with_in_range:
            brake_data = await crudeController.add_attendance_break_module_crud_module(
                db=db, data=data, active_session_id=active_session.id
            )

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
                    "message": ERROR_MESSAGE.ATTENDANCE_MODULE.OUT_OF_RANGE_ATTENDANCE_PUNCH,
                    "success": SUCCESS.FALSE,
                },
            )

    else:
        brake_data = await crudeController.add_attendance_break_module_crud_module(
            db=db, data=data, active_session_id=active_session.id
        )

        return {
            "message": SUCCESS_MESSAGE.BREAK_STARTED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": {
                "break_id": brake_data.id,
                "break_start_time": brake_data.break_start_time,
            },
        }


async def attendance_sessions_breaks_end_a_break_service_function(
    db: db_dependencies, data: AttendancePunchInPydantic, user: dict
):
    active_session = await crudeController.fetch_attendance_active_sessions_crude_service(db=db, user_id=user.id)

    if not active_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.NO_ACTIVE_ATTENDANCE_SESSION,
                "success": SUCCESS.FALSE,
            },
        )

    org_location_config_data = await crudeController.fetch_org_location_config_crude_service(
        db=db, organization_id=user.organization_id
    )

    if not org_location_config_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.NO_LOCATION_CONFIG_ADDED,
                "success": SUCCESS.FALSE,
            },
        )

    if not data.is_work_from_home:
        is_with_in_range = utils.calculate_org_emp_location_boundary(
            data=data, org_location_config_data=org_location_config_data
        )

        if is_with_in_range:
            wfo_break_data = await crudeController.fetch_attendance_active_break_crude_service(
                db=db, active_session_id=active_session.id
            )

            is_mislinious = utils.verify_is_punch_in_coords_are_mislinious(session_data=wfo_break_data, data=data)

            break_start_time = wfo_break_data.break_start_time
            if isinstance(wfo_break_data.break_start_time, str):
                break_start_time = datetime.fromisoformat(wfo_break_data.break_start_time)

            wfo_break_data.break_end_time = datetime.utcnow()
            wfo_break_data.total_break_minutes = (wfo_break_data.break_end_time - break_start_time).total_seconds() / 60
            wfo_break_data.punch_out_coordinates = json.dumps(data.location_coordinates.model_dump())
            wfo_break_data.is_mislinious = is_mislinious
            wfo_break_data.status = "completed"

            db.commit()

            return {
                "message": SUCCESS_MESSAGE.BREAK_ENDED_SUCCESSFULLY,
                "success": SUCCESS.TRUE,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.ATTENDANCE_MODULE.OUT_OF_RANGE_ATTENDANCE_PUNCH,
                    "success": SUCCESS.FALSE,
                },
            )
    else:
        wfh_break_data = await crudeController.fetch_attendance_active_break_crude_service(
            db=db, active_session_id=active_session.id
        )

        break_start_time = wfh_break_data.break_start_time
        if isinstance(wfh_break_data.break_start_time, str):
            break_start_time = datetime.fromisoformat(wfh_break_data.break_start_time)

        wfh_break_data.break_end_time = datetime.utcnow()
        wfh_break_data.total_break_minutes = (wfh_break_data.break_end_time - break_start_time).total_seconds() / 60
        wfh_break_data.punch_out_coordinates = json.dumps(data.location_coordinates.model_dump())
        wfh_break_data.is_mislinious = False
        wfh_break_data.status = "completed"

        db.commit()

        return {
            "message": SUCCESS_MESSAGE.BREAK_ENDED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
        }


async def attendance_session_punch_out_service_function(
    db: db_dependencies, data: AttendancePunchInPydantic, user: dict
):

    active_session = await crudeController.fetch_attendance_active_sessions_crude_service(db=db, user_id=user.id)

    if not active_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.NO_ACTIVE_ATTENDANCE_SESSION,
                "success": SUCCESS.FALSE,
            },
        )

    org_location_config_data = await crudeController.fetch_org_location_config_crude_service(
        db=db, organization_id=user.organization_id
    )

    if not org_location_config_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.NO_LOCATION_CONFIG_ADDED,
                "success": SUCCESS.FALSE,
            },
        )

    active_break = await crudeController.fetch_attendance_active_break_crude_service(
        db=db, active_session_id=active_session.id
    )

    is_mislinious: bool = False

    if not data.is_work_from_home:

        is_with_in_range = utils.calculate_org_emp_location_boundary(
            data=data, org_location_config_data=org_location_config_data
        )

        if is_with_in_range:
            is_mislinious = utils.verify_is_punch_in_coords_are_mislinious(data=data, session_data=active_session)

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": ERROR_MESSAGE.ATTENDANCE_MODULE.OUT_OF_RANGE_ATTENDANCE_PUNCH,
                    "success": SUCCESS.FALSE,
                },
            )

    await crudeController.attendance_punch_out_crude_helper(
        db=db, data=data, active_session=active_session, is_mislinious=is_mislinious, break_data=active_break
    )

    return {
        "message": SUCCESS_MESSAGE.ATTENDANCE_PUNCH_IN_SUCCESSFULLY,
        "success": SUCCESS.TRUE,
    }
