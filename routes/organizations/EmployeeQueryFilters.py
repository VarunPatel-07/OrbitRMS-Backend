import json

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import aliased

from models.sql import Models


def apply_query_filter(query, filters):

    conditions = []

    query = query.join(Models.User.personal_info)

    ReportingManager = None
    ReportingManagerInfo = None

    if any(f.get("field_name") in ["employee_type", "reporting_manager"] for f in filters):
        query = query.join(Models.User.employee_info)

    if any(f.get("field_name") == "reporting_manager" for f in filters):
        ReportingManager = aliased(Models.User)
        ReportingManagerInfo = aliased(Models.PersonalInfo)

        query = query.join(Models.EmployeeInfo.reporting_manager.of_type(ReportingManager)).join(
            ReportingManager.personal_info.of_type(ReportingManagerInfo)
        )

    for each_filter in filters:

        field_name = each_filter.get("field_name")
        operator = each_filter.get("operator")
        value = each_filter.get("value")

        #
        # * Here We Will Apply The Filter Based On The Name Of The Employee
        #
        if field_name == "employee_name":
            if operator == "equals" or operator == "is":
                normalized_db_name = Models.PersonalInfo.normalized_full_name
                normalized_input = value.strip().replace("  ", " ")
                conditions.append(normalized_db_name.ilike(f"%{normalized_input}%"))
            if operator == "contains":
                conditions.append(Models.PersonalInfo.full_name.ilike(f"%{value}%"))
            if operator == "starts_with":
                conditions.append(Models.PersonalInfo.full_name.ilike(f"{value}%"))
            if operator == "ends_with":
                conditions.append(Models.PersonalInfo.full_name.ilike(f"%{value}"))

        #
        # * Here We Will Apply The Filter Based On Account Status Is It Is Active Or Not
        #

        if field_name == "account_status":
            if operator == "equals" or operator == "is":
                if value == "Active":
                    conditions.append(Models.User.account_status == True)
                elif value == "Inactive":
                    conditions.append(Models.User.account_status == False)

        #
        # * Here We Will Apply The Filter Based On  Status Of The Employee Currently An Employee Have Four Status Like Intern, Trainee, Probation, Confirmed
        #

        if field_name == "status":
            if operator == "is":
                conditions.append(Models.EmployeeInfo.status.ilike(f"%{value}%"))

        #
        # * Here We Will Apply The Filter Based On  Type  Of The Employee Currently An Employee Have Four Type  Like   Technical, Non-Technical, Support And Management
        #

        if field_name == "employee_type":
            if operator == "equals" or operator == "is":

                normalized_db_name = func.replace(func.trim(Models.EmployeeInfo.employee_type), "  ", " ")

                if isinstance(value, str):
                    try:
                        parsed_value = json.loads(value)

                        if not isinstance(parsed_value, list):
                            parsed_value = [parsed_value]

                    except json.JSONDecodeError:
                        parsed_value[value]
                elif isinstance(value, list):

                    parsed_value = value

                else:

                    parsed_value = [str(value)]

                employee_type_array = []

                for val in parsed_value:

                    normalized_input = val.strip().replace("  ", " ")

                    employee_type_array.append(normalized_db_name.ilike(f"%{normalized_input}%"))

                if employee_type_array:
                    conditions.append(or_(*employee_type_array))

        #
        # * Here We Will Apply The Filter Based On  The Name Of The Reporting Manager
        #

        if field_name == "reporting_manager":

            if operator == "equals" or operator == "is":
                normalized_db_name = func.replace(func.trim(ReportingManagerInfo.full_name), "  ", " ")
                normalized_input = value.strip().replace("  ", " ")
                conditions.append(normalized_db_name.ilike(f"%{normalized_input}%"))

            if operator == "contains":
                conditions.append(ReportingManagerInfo.full_name.ilike(f"%{value}%"))

            if operator == "starts_with":
                conditions.append(ReportingManagerInfo.full_name.ilike(f"{value}%"))
            if operator == "ends_with":
                conditions.append(ReportingManagerInfo.full_name.ilike(f"%{value}"))

    if conditions:
        query = query.filter(and_(*conditions))
    return query
