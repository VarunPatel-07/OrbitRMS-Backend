from Helper.helper import (
    filter_fields,
)


def apply_client_inquiry_query_filter(query_data, filters):

    for each_filter in filters:
        field_name = each_filter.get("field_name")
        operator = each_filter.get("operator")
        value = each_filter.get("value")

        if operator == "is":
            if value == "Active":
                query_data = [item for item in query_data if item.data.get(field_name) is True]
            elif value == "Inactive":
                query_data = [item for item in query_data if item.data.get(field_name) is False]

        if operator == "equals":
            query_data = [item for item in query_data if str(item.data.get(field_name)) == value]

        if operator == "contains":
            query_data = [
                item
                for item in query_data
                if isinstance(item.data.get(field_name), (str, int))
                and value.lower() in str(item.data.get(field_name)).lower()
            ]

        if operator == "starts_with":
            query_data = [
                item
                for item in query_data
                if isinstance(item.data.get(field_name), (str, int))
                and str(item.data.get(field_name)).lower().startswith(value.lower())
            ]

        if operator == "ends_with":
            query_data = [
                item
                for item in query_data
                if isinstance(item.data.get(field_name), (str, int))
                and str(item.data.get(field_name)).lower().endswith(value.lower())
            ]
    return query_data
