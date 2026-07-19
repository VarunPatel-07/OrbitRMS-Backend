import math

from models.pydantic.HelperPydanticModel import DistanceCalculatorLatLong


def calculateDistanceWithHaversine(
    userLocation: DistanceCalculatorLatLong, orgLocation: DistanceCalculatorLatLong
) -> float:

    earthRadius = 6371000

    user_lat_rad = math.radians(userLocation.get("latitude"))
    org_lat_rad = math.radians(orgLocation.get("latitude"))
    delta_lat_rad = math.radians(orgLocation.get("latitude") - userLocation.get("latitude"))
    delta_lon_rad = math.radians(orgLocation.get("longitude") - userLocation.get("longitude"))

    haversine_accuracy = (
        math.sin(delta_lat_rad / 2) ** 2
        + math.cos(user_lat_rad) * math.cos(org_lat_rad) * math.sin(delta_lon_rad / 2) ** 2
    )

    central_angle = 2 * math.atan2(math.sqrt(haversine_accuracy), math.sqrt(1 - haversine_accuracy))

    return earthRadius * central_angle
