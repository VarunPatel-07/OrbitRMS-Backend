from email.utils import unquote
import json
import math
from sre_constants import SUCCESS

from database.Database import db_dependencies
from models.pydantic.Organizations.AttendancePydanticModal import (
    ApplyLeavePydanticModel,
    fetchAppliedLeavesQueryPydanticModel,
    getExistingLeavesHelperPydanticModel,
)
from utils.helper.helper import model_to_filtered_dict, parse_to_utc_date
from utils.responseMessages import ERROR_MESSAGE, SUCCESS_MESSAGE
from . import crude as crudeController
from . import utils
from fastapi import HTTPException, status


# ? APPLY LEAVE Handler
async def handle_apply_leave(
    db,
    user,
    data: ApplyLeavePydanticModel,
    documents=None,
    employee_id=None,
):
    start_date_utc = parse_to_utc_date(data.start_date)
    end_date_utc = parse_to_utc_date(data.end_date)
    current_date_utc = parse_to_utc_date(data.current_date)

    last_modified_by = model_to_filtered_dict(
        user.personal_info, ["user_id", "first_name", "last_name"]
    )

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

    if not existing_leave.success:
        raise HTTPException(
            status_code=existing_leave.status_code,
            detail={
                "message": existing_leave.message,
                "success": existing_leave.success,
            },
        )

    leave_type = await crudeController.get_leave(
        db=db, leave_type_id=data.leave_type_id, organization_id=user.organization_id
    )

    if not leave_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.NO_LEAVE_TYPE_FOUND,
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

    leave_balance = crudeController.get_leave_balance(
        db=db, leave_type_id=data.leave_type_id, query_user_id=query_user_id
    )

    if not leave_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.NO_LEAVE_TYPE_FOUND,
                "success": SUCCESS.FALSE,
            },
        )

    if leave_balance.available_leaves < total_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.INSUFFICIENT_LEAVE_BALANCE,
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


# ? FOR FETCHING ALL THE APPLIED LEAVES
async def fetch_user_leaves(
    db: db_dependencies, user: dict, query_data: fetchAppliedLeavesQueryPydanticModel
):
    filter_data = ""
    if query_data.filter:
        decoded = unquote(query_data.filter)
        filter_data = json.loads(decoded)

    employee_data = crudeController.get_employee_info(db=db, query_user_id=user.id)

    applied_leave = crudeController.get_applied_leave(db=db, query_user_id=user.id)

    total_data = applied_leave.count()
    page = page if page else 1
    limit = limit if limit else 10

    leaves = applied_leave.offset((page - 1) * limit).limit(limit).all()

    formatted_data = utils.formate_leave_data(
        leaves=leaves, filter_data=filter_data, employee_data=employee_data
    )

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

