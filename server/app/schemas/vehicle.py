from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from app.enums.license_status import LicenseStatus
from app.enums.license_type import LicenseType
from app.enums.vehicle_use import VehicleUse

class VehicleBase(BaseModel):
    vin: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = None
    body_type: Optional[str] = None

    vehicle_use: Optional[VehicleUse] = None
    blind_spot_warning_equipped: Optional[bool] = None

    days_per_week: Optional[int] = None
    one_way_miles: Optional[int] = None

    annual_mileage: Optional[int] = None

    license_type: Optional[LicenseType] = None
    license_status: Optional[LicenseStatus] = None

class VehicleCreate(VehicleBase):
    session_id: int

class VehicleUpdate(VehicleBase):
    pass

class VehicleResponse(VehicleBase):
    vehicle_id: int
    session_id: int

    class Config:
        from_attributes = True
