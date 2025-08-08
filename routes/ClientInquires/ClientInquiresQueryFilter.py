import json

from sqlalchemy import and_, func, or_

from Helper.helper import (
    filter_fields,
)
from SqlModels import Models


def apply_client_inquiry_query_filter(query_data, filters):

    for each_filter in filters:
        field_name = each_filter.get("field_name")
        operator = each_filter.get("operator")
        value = each_filter.get("value")

        if field_name == "form_id":
            conditions = []
            if operator == "equals" or operator == "is":

                normalized_db_name = func.replace(
                    func.trim(Models.ClientInquiresData.form_id), "  ", " "
                )

                if isinstance(value, str):
                    try:
                        parsed_value = json.loads(value)

                        if not isinstance(parsed_value, list):
                            parsed_value = [parsed_value]

                    except json.JSONDecodeError:
                        parsed_value = [value]
                elif isinstance(value, list):

                    parsed_value = value

                else:

                    parsed_value = [str(value)]

                form_id_array = []

                for val in parsed_value:

                    normalized_input = val.strip().replace("  ", " ")

                    form_id_array.append(normalized_db_name.ilike(f"%{normalized_input}%"))

                if form_id_array:
                    conditions.append(or_(*form_id_array))

        if field_name == "form_name":
            conditions = []
            if operator == "equals" or operator == "is":

                normalized_db_name = func.replace(
                    func.trim(Models.ClientInquiresData.form_name), "  ", " "
                )

                if isinstance(value, str):
                    try:
                        parsed_value = json.loads(value)

                        if not isinstance(parsed_value, list):
                            parsed_value = [parsed_value]

                    except json.JSONDecodeError:
                        parsed_value = [value]
                elif isinstance(value, list):

                    parsed_value = value

                else:

                    parsed_value = [str(value)]

                form_name_array = []

                for val in parsed_value:

                    normalized_input = val.strip().replace("  ", " ")

                    form_name_array.append(normalized_db_name.ilike(f"%{normalized_input}%"))

                if form_name_array:
                    conditions.append(or_(*form_name_array))

        if operator == "is":
            if value == "Active":
                conditions = [item for item in conditions if item.data.get(field_name) is True]
            elif value == "Inactive":
                conditions = [item for item in conditions if item.data.get(field_name) is False]

        if operator == "equals":
            conditions = [item for item in conditions if str(item.data.get(field_name)) == value]

        if operator == "contains":
            conditions = [
                item
                for item in conditions
                if isinstance(item.data.get(field_name), (str, int))
                and value.lower() in str(item.data.get(field_name)).lower()
            ]

        if operator == "starts_with":
            conditions = [
                item
                for item in conditions
                if isinstance(item.data.get(field_name), (str, int))
                and str(item.data.get(field_name)).lower().startswith(value.lower())
            ]

        if operator == "ends_with":
            conditions = [
                item
                for item in conditions
                if isinstance(item.data.get(field_name), (str, int))
                and str(item.data.get(field_name)).lower().endswith(value.lower())
            ]
    if conditions:
        query_data = query_data.filter(and_(*conditions))
    return query_data
