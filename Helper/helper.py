import secrets
from typing import List, Optional, Dict, Union
from sqlalchemy.orm import class_mapper
from sqlalchemy.ext.declarative import DeclarativeMeta


def generate_full_name(first_name: str, last_name: str, middle_name: str = None) -> str:
    return f"{first_name} {middle_name} {last_name}"


def generate_random_secret_key() -> str:
    generated_secret_key = secrets.token_urlsafe(16)
    print(generated_secret_key)
    return generated_secret_key


def filter_fields(
    module: Union[dict, object], fields: Optional[List[str]] = []
) -> Dict[str, str]:
    # Ensure module is a dictionary or an object with attributes
    if not isinstance(module, (dict, object)):
        raise ValueError(
            "The module must be a dictionary or an object with attributes."
        )

    # If module is an object, convert it to a dictionary
    if not isinstance(module, dict):
        if hasattr(module, "__dict__"):
            module = vars(module)  # Convert object attributes to a dictionary
        else:
            raise ValueError(
                f"Object of type {type(module)} does not have attributes to convert to a dictionary."
            )

    # Split fields into include and exclude lists
    exclude_fields: List[str] = []
    include_fields: List[str] = []

    for field in fields:
        if field.startswith("-"):
            exclude_fields.append(field.lstrip("-"))
        else:
            include_fields.append(field)

    # Apply the filtering logic
    if exclude_fields and include_fields:
        # Exclude the excluded fields and include the included fields
        filter_data = {
            key: value
            for key, value in module.items()
            if key not in exclude_fields
            and (key in include_fields or not include_fields)
        }
    elif exclude_fields:
        # Only exclude specified fields
        filter_data = {
            key: value for key, value in module.items() if key not in exclude_fields
        }
    elif include_fields:
        # Only include specified fields
        filter_data = {
            key: value for key, value in module.items() if key in include_fields
        }
    else:
        # No fields specified, return all data
        filter_data = {key: value for key, value in module.items()}

    return filter_data


def model_to_filtered_dict(data, fields: Optional[List[str]] = []) -> Dict[str, str]:

    if not isinstance(data.__class__, DeclarativeMeta):
        raise ValueError("The module must be a sql model")

    exclude_fields = [field.lstrip("-") for field in fields if field.startswith("-")]
    include_fields = [field for field in fields if not field.startswith("-")]

    result = {}

    for column in class_mapper(data.__class__).columns:

        column_name = column.key

        if exclude_fields and column_name in exclude_fields:
            continue

        if include_fields and column_name not in include_fields:
            continue

        result[column_name] = getattr(data, column_name)

    return result
