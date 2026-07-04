from datetime import date
import json
import math
from email.utils import unquote
from typing import Optional

from fastapi import HTTPException, status

from constants.constant import SUCCESS
from database.Database import db_dependencies
from models.pydantic.Organizations.AttendancePydanticModal import (
    ApplyLeavePydanticModel,
    fetchAppliedLeavesQueryPydanticModel,
    fetchAppliedOrganizationLeave,
    getExistingLeavesHelperPydanticModel,
    updateLeavesQueryPydanticModel,
)
from models.sql import Models
from routes.organizations.attendance.leave.queryFilters import (
    apply_organization_leave_sql_filters,
    apply_team_leave_sql_filters,
    attendance_leave_team_organization_query_filter,
)
from utils.helper.helper import model_to_filtered_dict, parse_to_utc_date
from utils.responseMessages import ERROR_MESSAGE, SUCCESS_MESSAGE


from routes.organizations.attendance.leave import crude as crudeController

from routes.organizations.attendance.leave import utils


# 1. handle_apply_leave(db, user, data, documents, employee_id): Apply leave for the current user or selected employee.
async def handle_apply_leave_service_function(
    db,
    user,
    data: ApplyLeavePydanticModel,
    documents=None,
    employee_id=None,
):
    start_date_utc = parse_to_utc_date(data.start_date)
    end_date_utc = parse_to_utc_date(data.end_date)
    current_date_utc = parse_to_utc_date(data.current_date)

    last_modified_by = model_to_filtered_dict(user.personal_info, ["user_id", "first_name", "last_name"])

    query_user_id = employee_id if employee_id else user.id

    existing_leave = await crudeController.get_existing_leaves(
        db=db,
        data=getExistingLeavesHelperPydanticModel(
            query_user_id=query_user_id,
            start_date=data.start_date,
            start_half=data.start_half,
            end_date=data.end_date,
            end_half=data.end_half,
        ),
    )

    if not existing_leave.get("success"):
        raise HTTPException(
            status_code=existing_leave.get("status_code"),
            detail={
                "message": existing_leave.get("message"),
                "success": existing_leave.get("success"),
            },
        )

    leave_type = await crudeController.get_leave(
        db=db, leave_type_id=data.leave_type_id, organization_id=user.organization_id
    )

    if not leave_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.NO_LEAVE_TYPE_FOUND,
                "success": SUCCESS.FALSE,
            },
        )

    diff_btw_date = (start_date_utc - current_date_utc).days
    is_planned = diff_btw_date > 5

    total_days = utils.calculate_total_days(
        start_date_utc=start_date_utc,
        end_date_utc=end_date_utc,
        start_half=data.start_half,
        end_half=data.end_half,
    )

    leave_balance = await crudeController.get_leave_balance(
        db=db, leave_type_id=data.leave_type_id, query_user_id=query_user_id
    )

    if not leave_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.NO_LEAVE_TYPE_FOUND,
                "success": SUCCESS.FALSE,
            },
        )

    if leave_balance.available_leaves < total_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.INSUFFICIENT_LEAVE_BALANCE,
                "success": SUCCESS.FALSE,
            },
        )

    leave_balance.available_leaves = leave_balance.available_leaves - total_days

    await crudeController.apply_leave_func(
        db=db,
        data=data,
        is_planned=is_planned,
        total_days=total_days,
        query_user_id=query_user_id,
        last_modified_by=last_modified_by,
        documents=documents,
    )

    return {
        "message": SUCCESS_MESSAGE.LEAVE_APPLIED_SUCCESSFULLY,
        "success": SUCCESS.TRUE,
    }


# 2. fetch_user_leaves(db, user, query_data): Fetch paginated applied leaves for the logged-in user.
async def fetch_user_leaves(db: db_dependencies, user: dict, query_data: fetchAppliedLeavesQueryPydanticModel):
    filter_data = ""
    if query_data.filter:
        decoded = unquote(query_data.filter)
        filter_data = json.loads(decoded)

    employee_data = await crudeController.get_employee_info(db=db, query_user_id=user.id)

    applied_leave = await crudeController.get_applied_leave(db=db, query_user_id=user.id)

    total_data = applied_leave.count()
    page = query_data.page if query_data.page else 1
    limit = query_data.limit if query_data.limit else 10

    leaves = applied_leave.offset((page - 1) * limit).limit(limit).all()

    formatted_data = utils.formate_leave_data(leaves=leaves, filter_data=filter_data, employee_data=employee_data)

    return {
        "message": SUCCESS_MESSAGE.USER_VERIFIED_SUCCESSFULLY,
        "success": SUCCESS.TRUE,
        "data": formatted_data,
        "metadata": {
            "total_data": total_data,
            "total_pages": math.ceil(total_data / limit),
            "current_page": page,
            "record_per_page": limit,
        },
    }


# 3. fetch_organization_leaves(db, user, query_data): Fetch organization leave data for the requested date/page.
async def fetch_organization_leaves(
    db: db_dependencies,
    user: dict,
    query_data: fetchAppliedOrganizationLeave,
):
    query_data = await crudeController.get_leaves_data(
        db=db, org_id=query_data.org_id, page=query_data.page, limit=query_data.limit
    )

    users_data = []

    for data in query_data.get("data"):
        if data.applied_leaves:
            for leave in data.applied_leaves:
                if leave.start_date <= query_data.date <= leave.end_date:
                    users_data.append(leave)

    return {
        "message": SUCCESS_MESSAGE.LEAVES_FETCHED_SUCCESSFULLY,
        "success": SUCCESS.TRUE,
        "data": users_data,
        "metadata": query_data.get("metadata"),
    }


# 4. fetch_employee_leaves_balance_service(db, user, employee_id): Fetch leave balance for the user or selected employee.
async def fetch_employee_leaves_balance_service(
    db: db_dependencies,
    user: dict,
    employee_id: Optional[str],
):
    query_id = employee_id if employee_id else user.id

    target_user_data = await crudeController.fetch_target_user_data(db=db, query_id=query_id)

    query_data = await crudeController.fetch_leaves_balance_data(db=db, query_id=query_id)

    data = utils.formate_employee_balance_data(user=target_user_data, query_data=query_data)

    return {
        "message": SUCCESS_MESSAGE.LEAVES_FETCHED_SUCCESSFULLY,
        "success": SUCCESS.TRUE,
        "data": data,
    }


# 5. fetch_team_member_leaves_service(db, user, query_data): Fetch team member leaves and team summary for a manager.
async def fetch_team_member_leaves_service(
    db: db_dependencies, user: dict, query_data: fetchAppliedLeavesQueryPydanticModel
):
    filter_data = None

    if query_data.filter:
        decoded = unquote(query_data.filter)
        filter_data = json.loads(decoded)

    offset = (query_data.page - 1) * query_data.limit

    leaves_query = await crudeController.get_team_members_leaves_service(db=db, user_id=user.id)

    if filter_data:
        leaves_query = attendance_leave_team_organization_query_filter(
            leave_query=leaves_query,
            filter_data=filter_data,
        )

    total_data = leaves_query.count()

    leaves_query_data = (
        leaves_query.order_by(Models.AttendanceLeavesModule.created_at.desc())
        .offset(offset)
        .limit(query_data.limit)
        .all()
    )

    data = utils.formate_team_members_leave_data(query_data=leaves_query_data)

    team_summary_base_query = await crudeController.get_team_data_summary(db=db, manager_id=user.id)

    if filter_data:
        team_summary_base_query = apply_team_leave_sql_filters(
            leave_query=team_summary_base_query,
            filter_data=filter_data,
        )

    total_employee = await crudeController.get_total_employee_data(db=db, manager_id=user.id)

    team_summary = utils.formate_team_summary_data(base_query=team_summary_base_query, total_employees=total_employee)

    return {
        "message": SUCCESS_MESSAGE.USER_VERIFIED_SUCCESSFULLY,
        "success": SUCCESS.TRUE,
        "data": {
            "applied_leaves": data,
            "team_summary": team_summary,
        },
        "metadata": {
            "total_data": total_data,
            "total_pages": math.ceil(total_data / query_data.limit) if query_data.limit else 0,
            "current_page": query_data.page,
            "record_per_page": query_data.limit,
        },
    }


# 6. fetch_organization_leaves_service(db, user, query_data): Fetch organization leaves and organization team summary.
async def fetch_organization_leaves_service(
    db: db_dependencies, user: dict, query_data: fetchAppliedLeavesQueryPydanticModel
):
    filter_data = None

    if query_data.filter:
        decoded = unquote(query_data.filter)
        filter_data = json.loads(decoded)

    offset = (query_data.page - 1) * query_data.limit

    org_leaves_query = await crudeController.get_total_leave_for_organization(
        db=db, organization_id=user.organization_id
    )

    if filter_data:
        org_leaves_query = attendance_leave_team_organization_query_filter(
            leave_query=org_leaves_query,
            filter_data=filter_data,
        )

    total_data = org_leaves_query.count()

    org_leaves_query_data = (
        org_leaves_query.order_by(Models.AttendanceLeavesModule.created_at.desc())
        .offset(offset)
        .limit(query_data.limit)
        .all()
    )

    formatted_leaves_data = utils.formate_organization_employee_leaves_data(org_leaves_query=org_leaves_query_data)

    org_emp_summary_base_query = await crudeController.org_emp_leaves_base_query(
        db=db, organization_id=user.organization_id
    )

    if filter_data:
        org_emp_summary_base_query = apply_organization_leave_sql_filters(
            leave_query=org_emp_summary_base_query,
            filter_data=filter_data,
        )

    org_emp_total_data = await crudeController.get_org_emp_total(db=db, organization_id=user.organization_id)

    emp_leaves_summary = utils.formate_organization_employee_leaves_summary(
        org_base_query=org_emp_summary_base_query, total_employees=org_emp_total_data
    )

    return {
        "message": SUCCESS_MESSAGE.USER_VERIFIED_SUCCESSFULLY,
        "success": SUCCESS.TRUE,
        "data": {
            "applied_leaves": formatted_leaves_data,
            "team_summary": emp_leaves_summary,
        },
        "metadata": {
            "total_data": total_data,
            "total_pages": math.ceil(total_data / query_data.limit) if total_data else 0,
            "current_page": query_data.page,
            "record_per_page": query_data.limit,
        },
    }


# 7. fetch_organization_leaves_service(db, user, query_data): Fetch organization leaves and organization team summary.
async def update_leave_request_service_function(
    db: db_dependencies,
    user: dict,
    query_data: updateLeavesQueryPydanticModel,
):
    base_query = await crudeController.get_leave_query_data(db=db, leave_id=query_data.leave_id)

    reporting_manager_id = base_query.user.employee_info.reporting_to_id

    if base_query.status in ["rejected", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.LEAVE_REQUEST_NOT_ALLOWED,
                "success": SUCCESS.FALSE,
            },
        )

    if not reporting_manager_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.NOT_AUTHORIZED_TO_MANAGE_LEAVE_UPDATE,
                "success": SUCCESS.FALSE,
            },
        )

    if not query_data.leave_status in ["pending", "approved", "rejected", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.PLEASE_PROVIDE_APPROPRIATE_LEAVE_STATUS,
                "success": SUCCESS.FALSE,
            },
        )

    updated_created_by_user = model_to_filtered_dict(user.personal_info, ["user_id", "first_name", "last_name"])

    base_query.status = query_data.leave_status
    base_query.updated_by = json.dumps(updated_created_by_user)

    if query_data.leave_status in ["rejected", "cancelled"]:

        leave_balance = await crudeController.get_leave_balance(
            db=db, query_user_id=base_query.user_id, leave_type_id=base_query.leave_type_id
        )

        if not leave_balance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": ERROR_MESSAGE.ATTENDANCE_MODULE.LEAVE_BALANCE_NOT_FOUND,
                    "success": SUCCESS.FALSE,
                },
            )

        leave_balance.available_leaves += base_query.total_days

    db.commit()

    return {
        "message": f"Leave {query_data.leave_status} Successfully",
        "success": SUCCESS.TRUE,
        "data": {},
    }


async def fetch_leaves_type_service(db: db_dependencies, user: dict):
    base_query = await crudeController.fetch_leave_types_crud_service(db=db, user=user)

    data = [leave_code for (leave_code,) in base_query]

    return {
        "message": SUCCESS_MESSAGE.USER_VERIFIED_SUCCESSFULLY,
        "success": SUCCESS.TRUE,
        "data": data,
    }
