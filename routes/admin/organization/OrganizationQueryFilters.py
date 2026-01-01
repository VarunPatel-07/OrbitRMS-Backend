import json

from sqlalchemy import and_, func, or_

from models.sql import Models


def Apply_Organization_Query_Filter(query, filters):
    conditions = []

    for each_filter in filters:
        field_name = each_filter.get("field_name")
        operator = each_filter.get("operator")
        value = each_filter.get("value")

        #
        # * Now Firstly We Will Check For The Organization With The Organization Name
        #
        if field_name == "organization_name":
            if operator == "equals" or operator == "is":
                normalized_db_name = func.replace(
                    func.trim(Models.OrganizationGeneralInfo.organization_name), "  ", " "
                )
                normalized_input = value.strip().replace("  ", " ")
                conditions.append(normalized_db_name.ilike(f"%{normalized_input}%"))

            if operator == "contains":
                conditions.append(
                    Models.OrganizationGeneralInfo.organization_name.ilike(f"%{value}%")
                )

            if operator == "starts_with":
                conditions.append(
                    Models.OrganizationGeneralInfo.organization_name.ilike(f"{value}%")
                )

            if operator == "ends_with":
                conditions.append(
                    Models.OrganizationGeneralInfo.organization_name.ilike(f"%{value}")
                )

        #
        # * Now We Will Check For The Organization With The Primary Email
        #

        if field_name == "primary_email":

            if operator == "equals" or operator == "is":
                normalized_db_name = func.replace(
                    func.trim(Models.OrganizationGeneralInfo.primary_email), "  ", " "
                )
                normalized_input = value.strip().replace("  ", " ")
                conditions.append(normalized_db_name.ilike(f"%{normalized_input}%"))

            if operator == "contains":
                conditions.append(Models.OrganizationGeneralInfo.primary_email.ilike(f"%{value}%"))

            if operator == "starts_with":
                conditions.append(Models.OrganizationGeneralInfo.primary_email.ilike(f"{value}%"))

            if operator == "ends_with":
                conditions.append(Models.OrganizationGeneralInfo.primary_email.ilike(f"%{value}"))

        #
        # * Now We Will Check For The Organization With The Primary Number
        #

        if field_name == "primary_number":
            if operator == "equals" or operator == "is":
                normalized_db_name = func.replace(
                    func.trim(Models.OrganizationGeneralInfo.primary_number), "  ", " "
                )
                normalized_input = value.strip().replace("  ", " ")
                conditions.append(normalized_db_name.ilike(f"%{normalized_input}%"))

            if operator == "contains":
                conditions.append(Models.OrganizationGeneralInfo.primary_number.ilike(f"%{value}%"))

            if operator == "starts_with":
                conditions.append(Models.OrganizationGeneralInfo.primary_number.ilike(f"{value}%"))

            if operator == "ends_with":
                conditions.append(Models.OrganizationGeneralInfo.primary_number.ilike(f"%{value}"))

        #
        # * Now We Will Check For The Organization With That Is Verified With The MetaTag Or Not

        if field_name == "meta_verified":
            if operator == "equals" or operator == "is":

                if value == "Verified":
                    conditions.append(Models.OrganizationGeneralInfo.is_meta_verified == True)
                elif value == "Not Verified":
                    conditions.append(Models.OrganizationGeneralInfo.is_meta_verified == False)

        #
        # * Now We Will Check For The Organization With The Emil
        #

        if field_name == "email_verified":
            if operator == "equals" or operator == "is":

                if value == "Verified":
                    conditions.append(Models.OrganizationGeneralInfo.email_verified == True)
                elif value == "Not Verified":
                    conditions.append(Models.OrganizationGeneralInfo.email_verified == False)

            #
            # * Now We Will Check For The Organization With The Primary Number
            #

        if field_name == "country":
            if operator == "equals" or operator == "is":

                normalized_db_name = func.replace(
                    func.trim(Models.OrganizationAddress.country), "  ", " "
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

                county_conditions = []
                for val in parsed_value:

                    normalized_input = val.strip().replace("  ", " ")
                    county_conditions.append(normalized_db_name.ilike(f"%{normalized_input}%"))
                if county_conditions:
                    conditions.append(or_(*county_conditions))

    if conditions:
        query = query.filter(and_(*conditions))
    return query
