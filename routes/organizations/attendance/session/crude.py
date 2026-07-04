from datetime import date, datetime, timedelta
import json
from typing import Any, Optional

from database.Database import db_dependencies
from models.pydantic.Organizations.AttendancePydanticModal import AttendancePunchInPydantic
from models.sql import Models


async def fetch_attendance_active_sessions_crude_service(db: db_dependencies, user_id: str):
    active_session = (
        db.query(Models.AttendancePunchInOutModule)
        .filter(
            Models.AttendancePunchInOutModule.user_id == user_id,
            Models.AttendancePunchInOutModule.status == "active",
        )
        .first()
    )

    return active_session


async def fetch_attendance_active_break_crude_service(db: db_dependencies, active_session_id: str):
    active_break = (
        db.query(Models.AttendanceBreakModel)
        .filter(
            Models.AttendanceBreakModel.session_id == active_session_id,
            Models.AttendanceBreakModel.status == "active",
        )
        .first()
    )

    return active_break


async def fetch_today_sessions_crude_service(
    db: db_dependencies, user_id: str, today_start_date: str, today_end_date: str
):

    today_session = (
        db.query(Models.AttendancePunchInOutModule)
        .filter(
            Models.AttendancePunchInOutModule.user_id == user_id,
            Models.AttendancePunchInOutModule.punch_in_time >= today_start_date,
            Models.AttendancePunchInOutModule.punch_in_time < today_end_date,
        )
        .first()
    )

    return today_session


async def fetch_org_location_config_crude_service(db: db_dependencies, organization_id: str):
    query_data = (
        db.query(Models.OrganizationLocationsConfig)
        .filter(Models.OrganizationLocationsConfig.organization_id == organization_id)
        .all()
    )

    return query_data


async def add_attendance_punch_in_punch_out(db: db_dependencies, user_id: str, data: AttendancePunchInPydantic):
    attendance_data = Models.AttendancePunchInOutModule(
        user_id=user_id,
        punch_in_time=datetime.utcnow(),
        punch_in_coordinates=json.dumps(data.location_coordinates.model_dump()),
        is_work_from_home=data.is_work_from_home,
        status="active",
    )

    db.add(attendance_data)
    db.commit()
    db.refresh(attendance_data)

    return attendance_data


async def add_attendance_break_module_crud_module(
    db: db_dependencies, data: AttendancePunchInPydantic, active_session_id: str
):

    brake_data = Models.AttendanceBreakModel(
        session_id=active_session_id,
        break_start_time=datetime.utcnow(),
        status="active",
        punch_in_coordinates=json.dumps(data.location_coordinates.model_dump()),
    )
    db.add(brake_data)
    db.commit()
    db.refresh(brake_data)

    return brake_data


async def get_last_session_details_crude_service(
    db: db_dependencies,
    user_id: str,
):
    last_session = (
        db.query(Models.AttendancePunchInOutModule)
        .filter(Models.AttendancePunchInOutModule.user_id == user_id)
        .order_by(Models.AttendancePunchInOutModule.punch_in_time.desc())
        .first()
    )

    return last_session


async def fetch_attendance_punch_in_out_status(
    db: db_dependencies, user_id: str, start_of_month: datetime, end_of_month: datetime
):
    monthly_data = (
        db.query(Models.AttendancePunchInOutModule)
        .filter(
            Models.AttendancePunchInOutModule.user_id == user_id,
            Models.AttendancePunchInOutModule.punch_in_time >= start_of_month,
            Models.AttendancePunchInOutModule.punch_in_time < end_of_month,
        )
        .order_by(Models.AttendancePunchInOutModule.punch_in_time.desc())
        .all()
    )

    return monthly_data


async def attendance_punch_out_crude_helper(
    db: db_dependencies, active_session, data: AttendancePunchInPydantic, break_data: Optional[Any], is_mislinious: bool
):
    if break_data:

        break_start_time = break_data.break_start_time
        if isinstance(break_data.break_start_time, str):
            break_start_time = datetime.fromisoformat(break_data.break_start_time)

        break_data.break_end_time = datetime.utcnow()

        break_data.total_break_minutes = (break_data.break_end_time - break_start_time).total_seconds() / 60

        break_data.punch_out_coordinates = json.dumps(data.location_coordinates.model_dump())
        break_data.is_mislinious = False
        break_data.status = "completed"

    # * Now we are adding the data for the main session

    active_session.punch_out_time = datetime.utcnow()
    active_session.punch_out_coordinates = json.dumps(data.location_coordinates.model_dump())
    active_session.status = "completed"

    punch_in_time = active_session.punch_in_time
    if isinstance(active_session.punch_in_time, str):
        punch_in_time = datetime.fromisoformat(active_session.punch_in_time)

    punch_out_time = active_session.punch_out_time
    if isinstance(active_session.punch_out_time, str):
        punch_out_time = datetime.fromisoformat(active_session.punch_out_time)

    gross_seconds = (punch_out_time - punch_in_time).total_seconds()
    total_gross_minutes = int(gross_seconds // 60)

    total_break_minutes = sum([b.total_break_minutes or 0 for b in active_session.attendance_breaks])

    total_effective_minutes = max(0, total_gross_minutes - total_break_minutes)

    active_session.total_gross_minutes = round(total_gross_minutes, 2)
    active_session.total_break_minutes = round(total_break_minutes, 2)
    active_session.total_effective_minutes = total_effective_minutes
    active_session.session_completed = True

    active_session.is_mislinious = is_mislinious

    db.commit()
    db.refresh(active_session)
