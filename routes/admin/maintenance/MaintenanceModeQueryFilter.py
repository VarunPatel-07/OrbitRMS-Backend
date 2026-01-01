import json
from datetime import datetime

from sqlalchemy import and_, func, or_

from models.sql import Models


def MaintenanceModeQueryFilter(query, filters):

    conditions = []

    for each_filter in filters:

        field_name = each_filter.get("field_name")
        operator = each_filter.get("operator")
        value = each_filter.get("value")

        if field_name == "type":

            if operator == "equals" or operator == "is":

                normalized_db_name = func.replace(func.trim(Models.MaintenanceLog.type), "  ", " ")
                normalized_input = value.strip().replace("  ", " ")
                conditions.append(normalized_db_name.ilike(f"%{normalized_input}%"))

        if field_name == "status":
            if operator == "equals" or operator == "is":

                normalized_db_name = func.replace(
                    func.trim(Models.MaintenanceLog.status), "  ", " "
                )

                parsed_value = []

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

                status_conditions = []
                for val in parsed_value:

                    normalized_input = val.strip().replace("  ", " ")
                    status_conditions.append(normalized_db_name.ilike(f"%{normalized_input}%"))
                if status_conditions:
                    conditions.append(or_(*status_conditions))

        if field_name == "starting_date":

            if operator == "is":

                target_date = datetime.fromisoformat(value.replace("Z", "+00:00")).date()

                start_datetime = datetime.combine(target_date, datetime.min.time())
                end_datetime = datetime.combine(target_date, datetime.max.time())

                conditions.append(Models.MaintenanceLog.started_at >= start_datetime)
                conditions.append(Models.MaintenanceLog.started_at <= end_datetime)

            if operator == "between":
                try:

                    # Parse the stringified object
                    parsed_range = json.loads(value)

                    if not isinstance(parsed_range, object):
                        raise ValueError("Invalid Type")

                    start_str = parsed_range.get("start_date")
                    end_str = parsed_range.get("end_date")

                    if not start_str or not end_str:
                        raise ValueError("Both starting_date and ending_date must be provided")

                    # Convert both to datetime objects
                    start_datetime = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    end_datetime = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

                    conditions.append(Models.MaintenanceLog.started_at >= start_datetime)
                    conditions.append(Models.MaintenanceLog.started_at <= end_datetime)

                except (ValueError, json.JSONDecodeError) as e:
                    print("Invalid date format or JSON for 'between':", e)

        if field_name == "ending_date":

            if operator == "is":

                target_date = datetime.fromisoformat(value.replace("Z", "+00:00")).date()
                start_datetime = datetime.combine(target_date, datetime.min.time())
                end_datetime = datetime.combine(target_date, datetime.max.time())

                conditions.append(Models.MaintenanceLog.ended_at >= start_datetime)
                conditions.append(Models.MaintenanceLog.ended_at <= end_datetime)

            if operator == "between":
                try:

                    # Parse the stringified object
                    parsed_range = json.loads(value)

                    if not isinstance(parsed_range, object):
                        raise ValueError("Invalid Type")

                    start_str = parsed_range.get("start_date")
                    end_str = parsed_range.get("end_date")

                    if not start_str or not end_str:
                        raise ValueError("Both starting_date and ending_date must be provided")

                    # Convert both to datetime objects
                    start_datetime = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    end_datetime = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

                    conditions.append(Models.MaintenanceLog.ended_at >= start_datetime)
                    conditions.append(Models.MaintenanceLog.ended_at <= end_datetime)

                except (ValueError, json.JSONDecodeError) as e:
                    print("Invalid date format or JSON for 'between':", e)

    if conditions:
        query = query.filter(and_(*conditions))
    return query
