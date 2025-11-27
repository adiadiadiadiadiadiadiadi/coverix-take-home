from typing import Any
from sqlalchemy.orm import Session
from app.enums.license_status import LicenseStatus
from app.enums.license_type import LicenseType
from app.enums.vehicle_use import VehicleUse
from app.models.vehicle import Vehicle

def create_vehicle(db: Session, session_id: int):
    vehicle = Vehicle(session_id=session_id)
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)

    return vehicle

def save (
    vehicle_id: int,
    db: Session,
    attribute: str,
    value: Any
):
    veh = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    setattr(veh, attribute, value)
    db.commit()
    db.refresh(veh)