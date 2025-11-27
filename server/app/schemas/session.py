from typing import Optional
from pydantic import BaseModel

from app.enums.chat_step import ChatStep
from app.enums.vehicle_step import VehicleStep
from app.enums.license_status import LicenseStatus
from app.enums.license_type import LicenseType

class SessionBase(BaseModel):
    current_step: ChatStep
    vehicle_step: Optional[VehicleStep] = None

    zip_code: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None

    license_type: Optional[LicenseType] = None
    license_status: Optional[LicenseStatus] = None

class SessionCreate(BaseModel):
    pass

class SessionUpdate(BaseModel):
    current_step: Optional[ChatStep] = None
    vehicle_step: Optional[VehicleStep] = None

    zip_code: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None

    license_type: Optional[LicenseType] = None
    license_status: Optional[LicenseStatus] = None

class SessionResponse(SessionBase):
    session_id: int

    class Config:
        from_attributes = True