import secrets
from typing import List, Optional , Dict , Union


def generate_full_name(first_name:str , last_name:str = None) -> str:
 return f"{first_name} {last_name}"

def generate_random_secret_key()->str:
    generated_secret_key = secrets.token_urlsafe(16)
    print(generated_secret_key)
    return generated_secret_key

def filter_fields(module:Union[dict , object] , fields:Optional[List[str]] = None )->Dict[str , str]:
    
    
    if not isinstance(module, dict):
        if hasattr(module, '__dict__'):
            module = vars(module)
        else:
            raise ValueError("The module must be a dictionary or an object with attributes.")
    
    exclude_fields:List[str] = []
    include_fields:List[str] = []
    for field in fields:
        if field.startswith("-"):
            exclude_fields.append(field.lstrip("-"))
        else:
            include_fields.append(field)
    
    if len(exclude_fields) >=1 :
        filtered_data = {
            key: value for key  , value in module.items() if key not in exclude_fields
            }
        return filtered_data
    elif len(include_fields) >=1 :
        filtered_data = {
            key : value for key , value in module.items() if key in include_fields
            }
        return filtered_data
    else:
        filtered_data = {
            key: value for key , value in module.items()
            }
        return filtered_data