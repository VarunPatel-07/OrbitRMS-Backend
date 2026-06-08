from typing import List, Optional

from fastapi import Form
from yarl import Query

from models.pydantic.Organizations.AttendancePydanticModal import (
    ApplyLeavePydanticModel,
    fetchAppliedLeavesQueryPydanticModel,
)


def get_apply_leave_dependencies(
    leave_type_id: str = Form(...),
    start_date: str = Form(...),
    start_half: str = Form(...),
    end_date: str = Form(...),
    end_half: str = Form(...),
    current_date: str = Form(...),
    description: Optional[str] = Form(None),
    notify_to: Optional[List[str]] = Form(None),
):
    return ApplyLeavePydanticModel(
        leave_type_id=leave_type_id,
        start_date=start_date,
        start_half=start_half,
        end_date=end_date,
        end_half=end_half,
        current_date=current_date,
        description=description,
        notify_to=notify_to,
    )


def get_fetch_leaves_dependencies(
    page: int = Query(..., alias="page"),
    limit: int = Query(..., alias="limit"),
    filter: Optional[str] = Query(None, alias="filter"),
):
    return fetchAppliedLeavesQueryPydanticModel(page=page, limit=limit, filter=filter)
