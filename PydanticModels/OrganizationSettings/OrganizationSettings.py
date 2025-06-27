from pydantic import BaseModel
from datetime import datetime


class AddEditHolidayPydanticModel(BaseModel):
    holiday_name: str
    date: datetime
    year: int
