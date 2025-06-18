import base64
import hashlib
import os
import secrets
from typing import Dict, List, Optional, Union

from Crypto.Cipher import AES
from dotenv import load_dotenv
from fastapi import HTTPException, Request, status
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import class_mapper

import secrets
import string

from Database.Database import db_dependencies

load_dotenv(override=True)

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY").encode()


def generate_full_name(first_name: str, last_name: str, middle_name: str = None) -> str:
    return f"{first_name} {middle_name} {last_name}"


# * this is the function that will help to create random secret key


def generate_random_secret_key() -> str:
    generated_secret_key = secrets.token_urlsafe(16)

    return generated_secret_key


#  This function filters a specific field from the data.
#  To exclude a field, prepend it with a "-" (e.g., ['-password'] will remove the 'password' field).
#  If the "-" is not used (e.g., ['password']), the function will return the specified field.


def filter_fields(module: Union[dict, object], fields: Optional[List[str]] = []) -> Dict[str, str]:
    # Ensure module is a dictionary or an object with attributes
    if not isinstance(module, (dict, object)):
        raise ValueError("The module must be a dictionary or an object with attributes.")

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
            if key not in exclude_fields and (key in include_fields or not include_fields)
        }
    elif exclude_fields:
        # Only exclude specified fields
        filter_data = {key: value for key, value in module.items() if key not in exclude_fields}
    elif include_fields:
        # Only include specified fields
        filter_data = {key: value for key, value in module.items() if key in include_fields}
    else:
        # No fields specified, return all data
        filter_data = {key: value for key, value in module.items()}

    return filter_data


#  This function filters specific fields from the SQL model data.
#  To exclude a field, prepend it with a "-" (e.g., ['-password'] will remove the 'password' field from the model).
#  If the "-" is not used (e.g., ['password']), the function will include the specified field in the query result.


def model_to_filtered_dict(data, fields: Optional[List[str]] = []) -> Dict[str, str]:

    if data is None:
        return {}

    if fields is None:
        fields = []

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


# function to encode string | num  | dict into url-safe encoding


def urlsafe_data_encoding_function(data: dict | str) -> str:
    if not data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "The Data is required", "success": False},
        )

    # Convert dict to JSON string if necessary
    if isinstance(data, dict):
        data = json.dumps(data)

    cipher = AES.new(ENCRYPTION_KEY, AES.MODE_EAX)
    nonce = cipher.nonce
    ciphertext, tag = cipher.encrypt_and_digest(data.encode())
    return base64.urlsafe_b64encode(nonce + tag + ciphertext).decode()


# to decode url-safe encoded value


def urlsafe_data_decoding_function(encrypted_data: str) -> str:
    if not encrypted_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "The Data is required", "success": False},
        )

    try:
        row_data = base64.urlsafe_b64decode(encrypted_data)
        nonce = row_data[:16]  # First 16 bytes: Nonce
        tag = row_data[16:32]  # Next 16 bytes: Authentication tag
        ciphertext = row_data[32:]

        # Initialize AES cipher in EAX mode
        cipher = AES.new(ENCRYPTION_KEY, AES.MODE_EAX, nonce=nonce)
        decrypted_data = cipher.decrypt(ciphertext)
        cipher.verify(tag)  # Verify the integrity of the data

        # If decrypted data is already in bytes, directly decode it
        if isinstance(decrypted_data, bytes):
            return decrypted_data.decode()  # Assuming the original data is a string
        else:
            raise ValueError("Decrypted data is not in bytes format.")

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Decryption failed: Data may have been altered or corrupted!",
                "success": False,
                "error": str(e),
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": f"Unexpected error during decryption: {str(e)}",
                "success": False,
            },
        )


# this is the function to update the sql model data
def update_model_data(
    db: db_dependencies,
    model,
    model_id: str,
    updated_data: dict,
    id_field: str = "id",
    filter_fields: list = None,
):

    record = db.query(model).filter(getattr(model, id_field) == model_id).first()

    if not record:
        print(f"Record with {id_field}={model_id} not found")
        return None
    else:
        updated_data_dict = (
            updated_data.__dict__ if hasattr(updated_data, "__dict__") else updated_data
        )
        if not isinstance(updated_data_dict, dict):
            print(f"Expected updated_data to be a dict, but got {type(updated_data_dict)}")
            return None
        else:

            if filter_fields:
                include_field = set()
                exclude_field = set()

                for field in filter_fields:
                    if field.startswith("-"):
                        exclude_field.add(field.strip("-"))
                    else:
                        include_field.add(field)
                updated_data_dict = {
                    field: value
                    for field, value in updated_data_dict.items()
                    if (field in include_field and field not in exclude_field)
                }
            for field, value in updated_data_dict.items():
                if hasattr(record, field) and value is not None:
                    setattr(record, field, value)

            db.commit()
            db.refresh(record)
            return record


def get_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.headers.get("X-Real-IP", request.client.host)

    return ip


def hash_fingerprint(fingerprint: str) -> str:
    return hashlib.sha256(fingerprint.encode()).hexdigest()


def generate_api_secrets_api_key():
    api_key = "api_" + "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(24)
    )
    api_secret = secrets.token_urlsafe(32)

    return api_key, api_secret


def is_valid_type(value, field_type):
    try:
        if field_type == "string":
            return isinstance(value, str)
        elif field_type == "boolean":
            return isinstance(value, bool)
        elif field_type == "number":
            return isinstance(value, int)
        elif field_type == "array":
            return isinstance(value, List)
        elif field_type == "object":
            return isinstance(value, dict)
        elif field_type == "array of string":
            return isinstance(value, list) and all(isinstance(item, str) for item in value)
        elif field_type == "array of object":
            return isinstance(value, list) and all(isinstance(item, dict) for item in value)

        return False
    except:
        return False
