from typing import Dict, List, Optional

from pydantic import BaseModel


class AdminSignInPayload(BaseModel):
    email: str
    password: str


class AdminVerifyOTP(BaseModel):
    otp: str


class MaintenanceModeData(BaseModel):
    message: str
    reason: str


class ScheduleMaintenanceModeData(BaseModel):
    message: str
    reason: str
    started_at: str
    ended_at: str
