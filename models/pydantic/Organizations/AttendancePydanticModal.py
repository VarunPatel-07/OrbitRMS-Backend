from pydantic import BaseModel


class LocationCoordinatesPydanticModel(BaseModel):
    latitude: float
    longitude: float
    accuracy: float


class AttendancePunchInPydantic(BaseModel):
    location_coordinates: LocationCoordinatesPydanticModel
    is_work_from_home: bool
