import json
from datetime import datetime

from models.sql import Models
from utils.helper.helper import parse_to_utc_date


def attendance_leave_team_organization_query_filter(leave, employee_id, filter):
    for each_filter in filter:
        field_name = each_filter.get("field_name")
        operator = each_filter.get("operator")
        value = each_filter.get("value")

        # First We Will have the status we check for this
        if field_name == "status":
            if operator == "is":
                if leave.status.lower() != value.lower():
                    return False

        if field_name == "date":
            leave_start_date = parse_to_utc_date(leave.start_date)
            leave_end_date = parse_to_utc_date(leave.end_date)

            if operator == "is":
                query_date = datetime.fromisoformat(value).date()

                if not (leave_start_date == query_date or leave_end_date == query_date):
                    return False

            if operator == "between":
                date_value = json.loads(value)

                query_start_date = datetime.fromisoformat(date_value.get("start_date")).date()
                query_end_date = datetime.fromisoformat(date_value.get("end_date")).date()

                if not (leave_start_date <= query_end_date and leave_end_date >= query_start_date):
                    return False

        if field_name == "leave type":
            if operator == "is":

                leave_type_array = json.loads(value) if type(value) == str else []

                if leave.leave_type.leave_code not in leave_type_array:
                    return False

        if field_name == "employee":

            if operator == "is":

                selected_emp_id = json.loads(value) if type(value) == str else []

                if employee_id not in selected_emp_id:
                    return False

        return True


def attendance_self_leave_quey_filter(leave, filter):
    for each_filter in filter:
        field_name = each_filter.get("field_name")
        operator = each_filter.get("operator")
        value = each_filter.get("value")

        # First We Will have the status we check for this
        if field_name == "status":
            if operator == "is":
                if leave.status.lower() != value.lower():
                    return False

        if field_name == "date":
            leave_start_date = parse_to_utc_date(leave.start_date)
            leave_end_date = parse_to_utc_date(leave.end_date)

            if operator == "is":
                query_date = datetime.fromisoformat(value).date()

                if not (leave_start_date == query_date or leave_end_date == query_date):
                    return False

            if operator == "between":
                date_value = json.loads(value)

                query_start_date = datetime.fromisoformat(date_value.get("start_date")).date()
                query_end_date = datetime.fromisoformat(date_value.get("end_date")).date()

                if not (leave_start_date <= query_end_date and leave_end_date >= query_start_date):
                    return False

        if field_name == "leave type":
            if operator == "is":

                leave_type_array = json.loads(value) if type(value) == str else []

                if leave.leave_type.leave_code not in leave_type_array:
                    return False

        return True


def apply_team_leave_sql_filters(leave_query, filter_data: dict):
    status_filter = filter_data.get("status")
    leave_type_id = filter_data.get("leave_type_id")
    employee_id = filter_data.get("employee_id")
    from_date = filter_data.get("from_date")
    to_date = filter_data.get("to_date")

    if status_filter:
        leave_query = leave_query.filter(Models.AttendanceLeavesModule.status == status_filter)

    if leave_type_id:
        leave_query = leave_query.filter(Models.AttendanceLeavesModule.leave_type_id == leave_type_id)

    if employee_id:
        leave_query = leave_query.filter(Models.AttendanceLeavesModule.user_id == employee_id)

    if from_date:
        leave_query = leave_query.filter(Models.AttendanceLeavesModule.start_date >= from_date)

    if to_date:
        leave_query = leave_query.filter(Models.AttendanceLeavesModule.end_date <= to_date)

    return leave_query


def apply_organization_leave_sql_filters(leave_query, filter_data: dict):
    status_filter = filter_data.get("status")
    leave_type_id = filter_data.get("leave_type_id")
    employee_id = filter_data.get("employee_id")
    from_date = filter_data.get("from_date")
    to_date = filter_data.get("to_date")
    is_planned = filter_data.get("is_planned")

    if status_filter:
        leave_query = leave_query.filter(Models.AttendanceLeavesModule.status == status_filter)

    if leave_type_id:
        leave_query = leave_query.filter(Models.AttendanceLeavesModule.leave_type_id == leave_type_id)

    if employee_id:
        leave_query = leave_query.filter(Models.AttendanceLeavesModule.user_id == employee_id)

    if from_date:
        leave_query = leave_query.filter(Models.AttendanceLeavesModule.start_date >= from_date)

    if to_date:
        leave_query = leave_query.filter(Models.AttendanceLeavesModule.end_date <= to_date)

    if is_planned is not None:
        leave_query = leave_query.filter(Models.AttendanceLeavesModule.is_planned == is_planned)

    return leave_query
