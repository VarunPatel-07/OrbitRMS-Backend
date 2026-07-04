
from datetime import date, datetime, timedelta
import json

from constants.constant import SUCCESS
from models.pydantic.Organizations.AttendancePydanticModal import AttendancePunchInPydantic
from utils.helper.calculateDistanceWithHaversine import calculateDistanceWithHaversine
from utils.responseMessages import SUCCESS_MESSAGE


def calculate_org_emp_location_boundary(data: AttendancePunchInPydantic, org_location_config_data: list):
    is_with_in_range = False
    for location_config in org_location_config_data:

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

        allowed_radius_meters = location_config.allowed_radius_meters if location_config.allowed_radius_meters else 500

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

    return is_with_in_range


def formate_last_session_data(last_session):
    last_session_break_minutes = 0

    for data in last_session.attendance_breaks:
        if data.total_break_minutes:
            last_session_break_minutes += data.total_break_minutes
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


def formate_active_session_data(active_session):
    is_on_break: bool = False

    for breaks in active_session.attendance_breaks:
        if breaks.status == "active":
            is_on_break = True
            break

    total_break_minutes = 0

    for b in active_session.attendance_breaks:
        if b.total_break_minutes:
            total_break_minutes += b.total_break_minutes
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


def verify_is_punch_in_coords_are_mislinious(session_data, data: AttendancePunchInPydantic):
    punch_in_coords = json.loads(session_data.punch_in_coordinates) if session_data.punch_in_coordinates else None

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

    return is_mislinious
