from datetime import datetime

from pydantic import BaseModel


class AddEditHolidayPydanticModel(BaseModel):
    holiday_name: str
    date: datetime
    year: int
