from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased
from sqlalchemy import func

from SqlModels import Models


def apply_query_filter(query, filters):

    conditions = []

    ReportingManagerPersonalInfo = aliased(Models.PersonalInfo)

    for each_filter in filters:

        field_name = each_filter.get("field_name")
        operator = each_filter.get("operator")
        value = each_filter.get("value")

        if field_name == "employee_name":
            if operator == "equals":
                normalized_db_name = func.replace(
                    func.trim(Models.PersonalInfo.full_name), "  ", " "
                )
                normalized_input = value.strip().replace("  ", " ")
                conditions.append(normalized_db_name.ilike(f"%{normalized_input}%"))
            if operator == "contains":
                conditions.append(Models.PersonalInfo.full_name.ilike(f"%{value}%"))
            if operator == "starts_with":
                conditions.append(Models.PersonalInfo.full_name.ilike(f"{value}%"))
            if operator == "ends_with":
                conditions.append(Models.PersonalInfo.full_name.ilike(f"%{value}"))
        if field_name == "status":
            if operator == "equals":
                if value == "Active":
                    conditions.append(Models.User.account_status == True)
                elif value == "Inactive":
                    conditions.append(Models.User.account_status == False)

        if field_name == "employee_type":
            if operator == "equals":
                conditions.append(Models.EmployeeInfo.employee_type.ilike(f"%{value}%"))
        if field_name == "reporting_manager":
            if operator == "equals":
                conditions.append(ReportingManagerPersonalInfo.full_name.ilike(f"%{value}%"))
            if operator == "contains":
                conditions.append(ReportingManagerPersonalInfo.full_name.ilike(f"%{value}%"))
            if operator == "starts_with":
                conditions.append(ReportingManagerPersonalInfo.full_name.ilike(f"{value}%"))
            if operator == "ends_with":
                conditions.append(ReportingManagerPersonalInfo.full_name.ilike(f"%{value}"))

    if conditions:
        query = query.filter(and_(*conditions))
    return query
