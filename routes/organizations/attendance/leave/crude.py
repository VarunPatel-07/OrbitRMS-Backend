import json
import math
from re import L
import uuid
from typing import List, Optional, Dict

import cloudinary
from click import File
from fastapi import UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

from config.EnvConfig import EnvConfig
from constants.constant import SUCCESS
from database.Database import db_dependencies
from models.pydantic.HelperPydanticModel import CrudeFunctionReturnType
from models.pydantic.Organizations.AttendancePydanticModal import (
    ApplyLeavePydanticModel,
    getExistingLeavesHelperPydanticModel,
)
from models.sql import Models
from utils.responseMessages import ERROR_MESSAGE

cloudinary.config(
    cloud_name=EnvConfig.CLOUDINARY_CLOUD_NAME,
    api_key=EnvConfig.CLOUDINARY_API_KEY,
    api_secret=EnvConfig.CLOUDINARY_API_SECRET,
)


async def get_existing_leaves(
    db: db_dependencies,
    data: getExistingLeavesHelperPydanticModel,
) -> CrudeFunctionReturnType:
    existing_leaves = (
        db.query(Models.AttendanceLeavesModule)
        .filter(
            Models.AttendanceLeavesModule.user_id == data.query_user_id,
            Models.AttendanceLeavesModule.status != "rejected",
            Models.AttendanceLeavesModule.start_date <= data.end_date,
            Models.AttendanceLeavesModule.end_date >= data.start_date,
        )
        .all()
    )

    for applied_leave in existing_leaves:
        if applied_leave.start_date == data.start_date and applied_leave.end_date == data.end_date:
            if applied_leave.start_half == "first_half" and data.start_half == "first_half":
                return {
                    "message": ERROR_MESSAGE.ATTENDANCE_MODULE.LEAVE_REQUEST_ALREADY_APPLIED,
                    "success": SUCCESS.FALSE,
                    "status_code": status.HTTP_400_BAD_REQUEST,
                }
            if applied_leave.end_half == "second_half" and data.end_half == "second_half":
                return {
                    "message": ERROR_MESSAGE.ATTENDANCE_MODULE.LEAVE_REQUEST_ALREADY_APPLIED,
                    "success": SUCCESS.FALSE,
                    "status_code": status.HTTP_400_BAD_REQUEST,
                }
            if applied_leave.start_half == "first_half" and data.start_half == "second_half":
                pass
            if applied_leave.start_half == "first_half" and applied_leave.end_half == "second_half":
                return {
                    "message": ERROR_MESSAGE.ATTENDANCE_MODULE.LEAVE_REQUEST_ALREADY_APPLIED,
                    "success": SUCCESS.FALSE,
                    "status_code": status.HTTP_400_BAD_REQUEST,
                }

    return {
        "message": "No conflicting leaves",
        "success": SUCCESS.TRUE,
        "status_code": 200,
    }


async def get_employee_info(db: db_dependencies, query_user_id: str) -> Models.User:
    employee_data = (
        db.query(Models.User)
        .options(
            joinedload(Models.User.personal_info),
            joinedload(Models.User.employee_info)
            .joinedload(Models.EmployeeInfo.reporting_manager)
            .options(joinedload(Models.User.personal_info), joinedload(Models.User.employee_info)),
        )
        .filter(Models.User.id == query_user_id)
        .first()
    )
    return employee_data


async def get_applied_leave(db: db_dependencies, query_user_id: str):
    leave_query = (
        db.query(Models.AttendanceLeavesModule)
        .options(joinedload(Models.AttendanceLeavesModule.leave_type))
        .filter(Models.AttendanceLeavesModule.user_id == query_user_id)
        .order_by(Models.AttendanceLeavesModule.created_at.desc())
    )

    return leave_query


async def get_leave(db: db_dependencies, leave_type_id: str, organization_id: str):

    leave_type = (
        db.query(Models.LeavesSettings)
        .filter(
            Models.LeavesSettings.id == leave_type_id,
            Models.LeavesSettings.organization_id == organization_id,
            Models.LeavesSettings.status == True,
        )
        .first()
    )
    return leave_type


async def get_leave_balance(db: db_dependencies, leave_type_id: str, query_user_id: str):
    leave_balance = (
        db.query(Models.LeaveBalance)
        .filter(
            Models.LeaveBalance.leave_type_id == leave_type_id,
            Models.LeaveBalance.user_id == query_user_id,
        )
        .first()
    )
    return leave_balance


async def get_notify_employee(db: db_dependencies, notify_to: List[str]):
    notify_to_users_array = db.query(Models.User).filter(Models.User.id.in_(notify_to)).all()

    return notify_to_users_array


async def upload_leave_documents(upload_file: UploadFile):
    unique_public_id = str(uuid.uuid4())
    folder = "leave_documents"
    file_name = upload_file.filename

    result = cloudinary.uploader.upload(
        upload_file.file,
        resource_type="auto",
        public_id=unique_public_id,
        folder=folder,
    )

    public_id = result["public_id"]

    media_asset_url = f"{EnvConfig.ORBITRMS_MEDIA_SERVICE_BASE_URL}/{folder}/{unique_public_id}/{file_name}"

    return {
        "asset_id": result["asset_id"],
        "public_id": public_id,
        "file_name": file_name,
        "file_type": upload_file.content_type,
        "folder": folder,
        "original_url": result["secure_url"],
        "media_asset_url": media_asset_url,
    }


async def apply_leave_func(
    db: db_dependencies,
    data: ApplyLeavePydanticModel,
    is_planned: bool,
    total_days: float,
    query_user_id: str,
    last_modified_by: Dict[str, str],
    documents: Optional[List[UploadFile]] = File(None),
):
    uploaded_documents = []

    if documents:
        uploaded_documents = [await run_in_threadpool(upload_leave_documents, doc) for doc in documents]

    notify_employee = await get_notify_employee(db=db, notify_to=data.notify_to)

    leave_info = Models.AttendanceLeavesModule(
        leave_type_id=data.leave_type_id,
        start_date=data.start_date,
        start_half=data.start_half,
        is_planned=is_planned,
        end_date=data.end_date,
        end_half=data.end_half,
        description=data.description,
        notify_to_users=notify_employee,
        documents=json.dumps(uploaded_documents),
        total_days=total_days,
        status="pending",
        user_id=query_user_id,
        created_by=json.dumps(last_modified_by),
    )

    db.add(leave_info)

    db.commit()


async def get_leaves_data(db: db_dependencies, org_id: str, page: int, limit: int):

    offset = (page - 1) * limit

    query = db.query(Models.User).filter(Models.User.organization_id == org_id)

    total_count = query.count()

    users = query.offset(offset).limit(limit).all()

    return {
        "data": users,
        "metadata": {
            "total_data": total_count,
            "total_pages": math.ceil(total_count / limit),
            "current_page": page,
            "record_per_page": limit,
        },
    }


async def fetch_leaves_balance_data(db: db_dependencies, query_id: str):
    query_data = db.query(Models.LeaveBalance).filter(Models.LeaveBalance.user_id == query_id).all()
    return query_data


async def fetch_target_user_data(db: db_dependencies, query_id: str):
    query_data = db.query(Models.User).filter(Models.User.id == query_id).first()
    return query_data


async def get_team_members_leaves_service(db: db_dependencies, user_id: str):
    query_data = (
        db.query(Models.AttendanceLeavesModule)
        .join(Models.User, Models.AttendanceLeavesModule.user_id == Models.User.id)
        .join(Models.EmployeeInfo, Models.EmployeeInfo.user_id == Models.User.id)
        .filter(Models.EmployeeInfo.reporting_to_id == user_id)
        .options(
            joinedload(Models.AttendanceLeavesModule.leave_type),
            joinedload(Models.AttendanceLeavesModule.user).joinedload(Models.User.personal_info),
            joinedload(Models.AttendanceLeavesModule.user)
            .joinedload(Models.User.employee_info)
            .joinedload(Models.EmployeeInfo.reporting_manager)
            .joinedload(Models.User.personal_info),
            joinedload(Models.AttendanceLeavesModule.user).joinedload(Models.User.employee_info),
            selectinload(Models.AttendanceLeavesModule.notify_to_users).joinedload(Models.User.personal_info),
            selectinload(Models.AttendanceLeavesModule.notify_to_users).joinedload(Models.User.employee_info),
        )
    )

    return query_data


async def get_team_data_summary(db: db_dependencies, manager_id: str):
    base_query = (
        db.query(Models.AttendanceLeavesModule)
        .join(Models.User, Models.AttendanceLeavesModule.user_id == Models.User.id)
        .join(Models.EmployeeInfo, Models.EmployeeInfo.user_id == Models.User.id)
        .filter(Models.EmployeeInfo.reporting_to_id == manager_id)
    )

    return base_query


async def get_total_employee_data(db: db_dependencies, manager_id: str):
    total_employees = (
        db.query(func.count(Models.User.id))
        .join(Models.EmployeeInfo, Models.EmployeeInfo.user_id == Models.User.id)
        .filter(Models.EmployeeInfo.reporting_to_id == manager_id)
        .scalar()
    )

    return total_employees


async def get_total_leave_for_organization(db: db_dependencies, organization_id: str):
    leave_query = (
        db.query(Models.AttendanceLeavesModule)
        .join(
            Models.User,
            Models.AttendanceLeavesModule.user_id == Models.User.id,
        )
        .filter(Models.User.organization_id == organization_id)
        .options(
            joinedload(Models.AttendanceLeavesModule.leave_type),
            joinedload(Models.AttendanceLeavesModule.user).joinedload(Models.User.personal_info),
            joinedload(Models.AttendanceLeavesModule.user).joinedload(Models.User.employee_info),
            joinedload(Models.AttendanceLeavesModule.user)
            .joinedload(Models.User.employee_info)
            .joinedload(Models.EmployeeInfo.reporting_manager)
            .joinedload(Models.User.personal_info),
            joinedload(Models.AttendanceLeavesModule.user)
            .joinedload(Models.User.employee_info)
            .joinedload(Models.EmployeeInfo.reporting_manager)
            .joinedload(Models.User.employee_info),
            selectinload(Models.AttendanceLeavesModule.notify_to_users).joinedload(Models.User.personal_info),
            selectinload(Models.AttendanceLeavesModule.notify_to_users).joinedload(Models.User.employee_info),
        )
    )

    return leave_query


async def org_emp_leaves_base_query(db: db_dependencies, organization_id: str):
    base_query = (
        db.query(Models.AttendanceLeavesModule)
        .join(
            Models.User,
            Models.AttendanceLeavesModule.user_id == Models.User.id,
        )
        .filter(Models.User.organization_id == organization_id)
    )

    return base_query


async def get_org_emp_total(db: db_dependencies, organization_id: str):
    total_employees = (
        db.query(func.count(Models.User.id)).filter(Models.User.organization_id == organization_id).scalar()
    )

    return total_employees


async def get_leave_query_data(db: db_dependencies, leave_id: str):
    query_data = (
        db.query(Models.AttendanceLeavesModule)
        .options(joinedload(Models.AttendanceLeavesModule.user))
        .filter(Models.AttendanceLeavesModule.id == leave_id)
    ).first()

    return query_data


async def fetch_leave_types_crud_service(db: db_dependencies, user: dict):
    query_data = (
        db.query(Models.LeavesSettings.leave_code)
        .filter(Models.LeavesSettings.organization_id == user.organization_id, Models.LeavesSettings.status == True)
        .order_by(Models.LeavesSettings.leave_name.asc())
        .all()
    )

    return query_data
