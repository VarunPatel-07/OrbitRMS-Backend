from ast import List
from datetime import date
from sre_constants import SUCCESS
from typing import Any

from fastapi import HTTPException
from rich import status


from routes.organizations.attendance.leave.queryFilters import attendance_self_leave_quey_filter
from utils.helper.helper import filter_fields


def calculate_total_days(start_date_utc: date, end_date_utc: date, start_half: str, end_half: str):
    total_days = 0
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

    return total_days


def formate_leave_data(leaves: List, filter_data: Any, employee_data):

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
                    if employee_data.employee_info and employee_data.employee_info.reporting_manager
                    else {}
                ),
            }
        )

    return _data
