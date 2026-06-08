import base64
import hashlib
import json
import math
import os
import random
import re
import secrets
import string
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Union
from zoneinfo import ZoneInfo

from Crypto.Cipher import AES
from dotenv import load_dotenv
from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import class_mapper
from starlette.datastructures import UploadFile as StarletteUploadFile

from config.EnvConfig import EnvConfig
from database.Database import db_dependencies

load_dotenv(override=True)

ENCRYPTION_KEY = EnvConfig.ENCRYPTION_KEY.encode()


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

ALLOWED_FILE_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".odt",
    ".ods",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".rtf",
    ".txt",
}


ALLOWED_FILE_TYPES = {
    "application/pdf",
    # Word
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # OpenDocument
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    # PowerPoint
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # Excel
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    # RTF / TXT
    "application/rtf",
    "text/rtf",
    "text/plain",
}


MAX_FILE_SIZE = 2 * 1024 * 1024


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
            raise ValueError(f"Object of type {type(module)} does not have attributes to convert to a dictionary.")

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
        updated_data_dict = updated_data.__dict__ if hasattr(updated_data, "__dict__") else updated_data
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
    api_key = "api_" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24))
    api_secret = secrets.token_urlsafe(32)

    return api_key, api_secret


def is_valid_email(value):
    if not isinstance(value, str):
        return False

    value = value.strip()

    if not value:
        return False

    return bool(EMAIL_REGEX.match(value))


def get_file_extension(filename: str):
    return os.path.splitext(filename.lower())[1]


def get_upload_file_size(file: StarletteUploadFile):
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    return size


def is_valid_file(value):
    def validate_single_file(file):
        if isinstance(file, StarletteUploadFile):
            if not file.filename:
                return False

            file_extension = get_file_extension(file.filename)

            if file_extension not in ALLOWED_FILE_EXTENSIONS:
                return False

            if file.content_type and file.content_type not in ALLOWED_FILE_TYPES:
                return False

            file_size = get_upload_file_size(file)

            if file_size > MAX_FILE_SIZE:
                return False
            return True

        if isinstance(file, dict):
            filename = file.get("original_filename") or file.get("filename")
            content_type = file.get("content_type")

            if not filename:
                return False

            file_extension = get_file_extension(filename)

            if file_extension not in ALLOWED_FILE_EXTENSIONS:
                return False

            if content_type and content_type not in ALLOWED_FILE_TYPES:
                return False

            return True

        return False

    if isinstance(value, list):
        return len(value) > 0 and all(validate_single_file(file) for file in value)

    return validate_single_file(value)


def is_valid_type(value, field_type):
    print(value, field_type)
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
        elif field_type == "email":
            return is_valid_email(value)
        elif field_type == "file":
            return is_valid_file(value)

        return False
    except:
        return False


def validate_field(vale):
    if vale is None:
        return False
    if isinstance(vale, str) and vale.strip() == "":
        return False
    if isinstance(vale, (list, Dict)) and len(vale) == 0:
        return False
    return True


def generatePasswordResetToken():

    token = secrets.token_urlsafe(32)
    return token


def generateAdminSignature():
    token = secrets.token_urlsafe(16)
    return token


def generateAdminAccessCode(length: int):
    otp = "".join(random.choices(string.digits, k=length))
    return otp


def parse_iso_datetime(iso_str: str) -> datetime:
    if not iso_str.endswith("Z"):

        return iso_str
    iso_str = iso_str.replace("Z", "+00:00")
    date_time = datetime.fromisoformat(iso_str)
    return date_time.astimezone(ZoneInfo("UTC"))


def difference_between_dates(current_date, next_date):
    def parse_date(date):
        if isinstance(date, str):
            return datetime.fromisoformat(date.replace("Z", "+00:00"))
        elif isinstance(date, datetime):
            return date
        else:
            raise ValueError(f"Invalid date type: {type(date)}")

    current_date_obj = parse_date(current_date)
    next_date_obj = parse_date(next_date)

    difference = abs((current_date_obj - next_date_obj).total_seconds()) / 60
    return int(math.floor(difference))


def parse_date(date_str: str):
    if date_str.endswith("Z"):
        date_str = date_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(date_str)

    # Ensure all dates are offset-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt


def validate_time_difference(start_date: str, end_date: str):

    start_date = parse_date(start_date)
    end_date = parse_date(end_date)

    # Calculate the difference
    time_diff = start_date - end_date
    total_seconds = abs(time_diff.total_seconds())
    minutes = int(total_seconds // 60)

    return minutes


def redirect_with_error(portal_slug: str, code: str):
    base_url = f"{EnvConfig.FRONTEND_URL}/{portal_slug}/social-media"

    return RedirectResponse(url=(f"{base_url}" f"?status=error" f"&modal=oauthError" f"&code={code}"))


def parse_to_utc_date(date_str: str) -> date:
    try:

        if "T" not in date_str:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc).date()

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Invalid date format. Expected YYYY-MM-DD or ISO datetime {date_str}",
                "success": False,
            },
        )
