from typing import List, Optional

from pydantic import BaseModel


class LocationCoordinatesPydanticModel(BaseModel):
    latitude: float
    longitude: float
    accuracy: float


class AttendancePunchInPydantic(BaseModel):
    location_coordinates: LocationCoordinatesPydanticModel
    is_work_from_home: bool


class ApplyLeavePydanticModel(BaseModel):
    leave_type_id: str
    start_date: str
    start_half: str
    end_date: str
    end_half: str
    current_date: str
    description: Optional[str] = None
    notify_to: Optional[List[str]] = None


class getExistingLeavesHelperPydanticModel(BaseModel):
    query_user_id: str
    start_date: str
    start_half: str
    end_date: str
    end_half: str


class fetchAppliedLeavesQueryPydanticModel(BaseModel):
    page: int
    limit: int
    filter: Optional[str]
