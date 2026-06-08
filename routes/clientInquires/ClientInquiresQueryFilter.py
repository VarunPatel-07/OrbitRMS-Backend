from sqlalchemy import Boolean, String, and_, cast, func, or_

from models.sql import Models


def apply_client_inquiry_query_filter(query_data, filters):

    for each_filter in filters:
        field_name = each_filter.get("field_name")
        operator = each_filter.get("operator")
        value = each_filter.get("value")

        all_conditions = []

        if field_name in ["form_id", "form_name"]:
            normalized_db_name = func.replace(func.trim(getattr(Models.ClientInquiresData, field_name)), "  ", " ")

            values = value if isinstance(value, list) else [value]

            conditions = [normalized_db_name.ilike(f"%{v.strip()}%") for v in values]

            all_conditions.append(or_(*conditions))

        else:
            json_fields = cast(Models.ClientInquiresData.data[field_name].as_string(), String)

            if operator == "equals":

                all_conditions.append(json_fields == str(value))

            elif operator == "contains":

                all_conditions.append(json_fields.ilike(f"%{value}%"))

            elif operator == "starts_with":
                all_conditions.append(json_fields.ilike(f"{value}%"))

            elif operator == "ends_with":
                all_conditions.append(json_fields.ilike(f"%{value}"))

            elif operator == "is":
                if value == "Active":
                    all_conditions.append(json_fields.cast(Boolean) == True)
                elif value == "Inactive":
                    all_conditions.append(json_fields.cast(Boolean) == False)

    if all_conditions:
        query_data = query_data.filter(and_(*all_conditions))
    return query_data
