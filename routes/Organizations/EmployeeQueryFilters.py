from sqlalchemy import and_, or_
from SqlModels import Models
from sqlalchemy.orm import aliased


def apply_query_filter(query, filters):

    conditions = []

    ReportingManager = aliased(Models.User)

    ReportingManagerPersonalInfo = aliased(Models.PersonalInfo)

    query.join(Models.EmployeeInfo.reporting_manager.of_type(ReportingManager))
    query.join(ReportingManager.personal_info.of_type(ReportingManagerPersonalInfo))

    for each_filter in filters:

        field_name = each_filter.get("field_name")
        operator = each_filter.get("operator")
        value = each_filter.get("value")

        if field_name == "employee_name":
            if operator == "equals":
                conditions.append(Models.PersonalInfo.full_name == value)
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
                conditions.append(ReportingManagerPersonalInfo.full_name == value)
            if operator == "contains":
                conditions.append(ReportingManagerPersonalInfo.full_name.ilike(f"%{value}%"))
            if operator == "starts_with":
                conditions.append(ReportingManagerPersonalInfo.full_name.ilike(f"{value}%"))
            if operator == "ends_with":
                conditions.append(ReportingManagerPersonalInfo.full_name.ilike(f"%{value}"))

    if conditions:
        query = query.filter(and_(*conditions))
    return query
