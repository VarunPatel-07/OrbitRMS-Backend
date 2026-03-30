import json
from datetime import datetime

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
