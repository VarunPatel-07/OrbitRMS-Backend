from datetime import datetime
from typing import List

from pydantic import BaseModel


class AddEditHolidayPydanticModel(BaseModel):
    holiday_name: str
    date: datetime
    year: int


class CreateLeaveTypePydanticModel(BaseModel):
    leave_name: str
    leave_code: str
    is_paid: bool
    max_number_of_leave: int
    refill_quarterly: bool
    refill_from: str
    description: str
    gender: List[str]
    employee_status: List[str]
    marital_status: List[str]
    status: bool
