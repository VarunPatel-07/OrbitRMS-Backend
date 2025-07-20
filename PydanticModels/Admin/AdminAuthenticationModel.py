from typing import Dict, List, Optional

from pydantic import BaseModel


class AdminSignInPayload(BaseModel):
    email: str
    password: str


class AdminVerifyOTP(BaseModel):
    otp: str
