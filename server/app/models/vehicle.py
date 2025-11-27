from app.db.database import Base
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
from sqlalchemy import Enum as SAEnum
from app.enums.license_status import LicenseStatus
from app.enums.license_type import LicenseType
from app.enums.vehicle_use import VehicleUse

class Vehicle(Base):
    __tablename__ = "vehicles"

    vehicle_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.session_id"), nullable=False)

    vin = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    make = Column(String, nullable=True)
    body_type = Column(String, nullable=True)

    vehicle_use = Column(SAEnum(VehicleUse), nullable=True)
    blind_spot_warning_equipped = Column(Boolean, nullable=True)

    days_per_week = Column(Integer, nullable=True) # dependent on commuting use
    one_way_miles = Column(Integer, nullable=True) # to work/school

    annual_mileage = Column(Integer, nullable=True) # commercial use, farming, or business

    license_type = Column(SAEnum(LicenseType), nullable=True)
    license_status = Column(SAEnum(LicenseStatus), nullable=True) # personal or commercial license type
