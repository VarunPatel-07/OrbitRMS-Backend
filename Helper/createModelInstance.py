from typing import Type, Dict, Any, List
from pydantic import BaseModel


def cerate_model_instance(
    model: Type[BaseModel], data: Dict[str, Any], fields: List[str] = []
):

    if not isinstance(data, dict):
        data = vars(data)

    exclude_fields: List[str] = []
    include_fields: List[str] = []
    for field in fields:
        if field.startswith("-"):
            exclude_fields.append(field.lstrip("-"))
        else:
            include_fields.append(field)

    # now rendering the data
    if len(exclude_fields) >= 1:
        filtered_data = {
            key: value for key, value in data.items() if key not in exclude_fields
        }
        return model(**filtered_data)
    elif len(include_fields) >= 1:
        filtered_data = {
            key: value for key, value in data.items() if key in include_fields
        }
        return model(**filtered_data)
    else:
        filtered_data = {key: value for key, value in data.items()}
        return model(**filtered_data)
