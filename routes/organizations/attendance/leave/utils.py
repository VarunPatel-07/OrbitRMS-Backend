from ast import List
from datetime import date
import json
from sre_constants import SUCCESS
from typing import Any

from fastapi import HTTPException
from rich import status
from sqlalchemy import and_, distinct, func, case

from models.sql import Models
from routes.organizations.attendance.leave.queryFilters import attendance_self_leave_quey_filter
from utils.helper.helper import filter_fields
from utils.responseMessages import ERROR_MESSAGE


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
                    "message": ERROR_MESSAGE.ATTENDANCE_MODULE.INVALID_LEAVE_HALF_SELECTION_FOR_SAME_DAY,
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


def formate_leave_data(leaves: List, filter_data: Any, employee_data) -> list:

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


def formate_employee_balance_data(user: dict, query_data: list) -> list:
    response_data = []
    for data in query_data:

        allowed_gender_list = json.loads(data.leave_type.gender) if data.leave_type.gender else []
        allowed_emp_status_list = json.loads(data.leave_type.employee_status) if data.leave_type.employee_status else []
        allowed_marital_status_list = (
            json.loads(data.leave_type.marital_status) if data.leave_type.marital_status else []
        )

        if (
            user.personal_info.gender in allowed_gender_list
            and user.employee_info.status in allowed_emp_status_list
            and user.family_info[0].marital_status in allowed_marital_status_list
        ):
            if data.leave_type.status:
                response_data.append(
                    {
                        **filter_fields(data, ["-leave_type", "-last_refill_date"]),
                        **filter_fields(
                            data.leave_type,
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

    return response_data


def formate_team_members_leave_data(query_data: list) -> list:
    data = []

    for leave in query_data:
        employee = leave.user

        data.append(
            {
                **filter_fields(
                    leave,
                    fields=[
                        "-leave_type",
                        "-notify_to_id",
                        "-user",
                    ],
                ),
                "leave_name": leave.leave_type.leave_name if leave.leave_type else None,
                "leave_code": leave.leave_type.leave_code if leave.leave_type else None,
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
                        if employee and employee.personal_info
                        else {}
                    ),
                    **(
                        filter_fields(
                            employee.employee_info,
                            fields=[
                                "employee_code",
                            ],
                        )
                        if employee and employee.employee_info
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
                            if employee.employee_info.reporting_manager.personal_info
                            else {}
                        ),
                        **(
                            filter_fields(
                                employee.employee_info.reporting_manager.employee_info,
                                fields=[
                                    "employee_code",
                                ],
                            )
                            if employee.employee_info.reporting_manager.employee_info
                            else {}
                        ),
                    }
                    if employee and employee.employee_info and employee.employee_info.reporting_manager
                    else {}
                ),
                "notify_to_users": [
                    {
                        **(
                            filter_fields(
                                notify_user.personal_info,
                                fields=[
                                    "first_name",
                                    "middle_name",
                                    "last_name",
                                    "full_name",
                                ],
                            )
                            if notify_user.personal_info
                            else {}
                        ),
                        **(
                            filter_fields(
                                notify_user.employee_info,
                                fields=["employee_code"],
                            )
                            if notify_user.employee_info
                            else {}
                        ),
                        "id": notify_user.id,
                    }
                    for notify_user in leave.notify_to_users
                ],
            }
        )

    return data


def formate_team_summary_data(base_query: list, total_employees: int):
    today = date.today()
    summary = base_query.with_entities(
        func.count(
            distinct(
                case(
                    (
                        and_(
                            Models.AttendanceLeavesModule.start_date <= today,
                            Models.AttendanceLeavesModule.end_date >= today,
                            Models.AttendanceLeavesModule.status.notin_(["cancelled", "rejected"]),
                        ),
                        Models.AttendanceLeavesModule.user_id,
                    )
                )
            )
        ).label("employees_on_leave"),
        func.count(
            case(
                (
                    Models.AttendanceLeavesModule.is_planned == True,
                    Models.AttendanceLeavesModule.id,
                )
            )
        ).label("planned_leaves"),
        func.count(
            case(
                (
                    Models.AttendanceLeavesModule.is_planned == False,
                    Models.AttendanceLeavesModule.id,
                )
            )
        ).label("unplanned_leaves"),
        func.count(
            case(
                (
                    Models.AttendanceLeavesModule.status == "pending",
                    Models.AttendanceLeavesModule.id,
                )
            )
        ).label("pending_leaves"),
        func.count(
            case(
                (
                    Models.AttendanceLeavesModule.status == "cancelled",
                    Models.AttendanceLeavesModule.id,
                )
            )
        ).label("cancelled_leaves"),
    ).first()

    return {
        "total_employees": total_employees or 0,
        "employees_on_leave": summary.employees_on_leave or 0,
        "planned_leaves": summary.planned_leaves or 0,
        "unplanned_leaves": summary.unplanned_leaves or 0,
        "pending_leaves": summary.pending_leaves or 0,
        "cancelled_leaves": summary.cancelled_leaves or 0,
    }


def formate_organization_employee_leaves_data(org_leaves_query: str):
    data = []

    for leave in org_leaves_query:
        employee = leave.user

        data.append(
            {
                **filter_fields(
                    leave,
                    fields=[
                        "-leave_type",
                        "-notify_to_id",
                        "-user",
                    ],
                ),
                "leave_name": leave.leave_type.leave_name if leave.leave_type else None,
                "leave_code": leave.leave_type.leave_code if leave.leave_type else None,
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
                        if employee and employee.personal_info
                        else {}
                    ),
                    **(
                        filter_fields(
                            employee.employee_info,
                            fields=[
                                "employee_code",
                            ],
                        )
                        if employee and employee.employee_info
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
                            if employee.employee_info.reporting_manager.personal_info
                            else {}
                        ),
                        **(
                            filter_fields(
                                employee.employee_info.reporting_manager.employee_info,
                                fields=[
                                    "employee_code",
                                ],
                            )
                            if employee.employee_info.reporting_manager.employee_info
                            else {}
                        ),
                    }
                    if employee and employee.employee_info and employee.employee_info.reporting_manager
                    else {}
                ),
                "notify_to_users": [
                    {
                        **(
                            filter_fields(
                                notify_user.personal_info,
                                fields=[
                                    "first_name",
                                    "middle_name",
                                    "last_name",
                                    "full_name",
                                ],
                            )
                            if notify_user.personal_info
                            else {}
                        ),
                        **(
                            filter_fields(
                                notify_user.employee_info,
                                fields=[
                                    "employee_code",
                                ],
                            )
                            if notify_user.employee_info
                            else {}
                        ),
                        "id": notify_user.id,
                    }
                    for notify_user in leave.notify_to_users
                ],
            }
        )

    return data


def formate_organization_employee_leaves_summary(org_base_query: list, total_employees: int):

    today = date.today()

    summary = org_base_query.with_entities(
        func.count(
            distinct(
                case(
                    (
                        and_(
                            Models.AttendanceLeavesModule.start_date <= today,
                            Models.AttendanceLeavesModule.end_date >= today,
                            Models.AttendanceLeavesModule.status.notin_(["cancelled", "rejected"]),
                        ),
                        Models.AttendanceLeavesModule.user_id,
                    ),
                    else_=None,
                )
            )
        ).label("employees_on_leave"),
        func.count(
            case(
                (
                    Models.AttendanceLeavesModule.is_planned == True,
                    Models.AttendanceLeavesModule.id,
                ),
                else_=None,
            )
        ).label("planned_leaves"),
        func.count(
            case(
                (
                    Models.AttendanceLeavesModule.is_planned == False,
                    Models.AttendanceLeavesModule.id,
                ),
                else_=None,
            )
        ).label("unplanned_leaves"),
        func.count(
            case(
                (
                    Models.AttendanceLeavesModule.status == "pending",
                    Models.AttendanceLeavesModule.id,
                ),
                else_=None,
            )
        ).label("pending_leaves"),
        func.count(
            case(
                (
                    Models.AttendanceLeavesModule.status == "cancelled",
                    Models.AttendanceLeavesModule.id,
                ),
                else_=None,
            )
        ).label("cancelled_leaves"),
    ).first()

    return {
        "total_employees": total_employees or 0,
        "employees_on_leave": summary.employees_on_leave or 0,
        "planned_leaves": summary.planned_leaves or 0,
        "unplanned_leaves": summary.unplanned_leaves or 0,
        "pending_leaves": summary.pending_leaves or 0,
        "cancelled_leaves": summary.cancelled_leaves or 0,
    }
