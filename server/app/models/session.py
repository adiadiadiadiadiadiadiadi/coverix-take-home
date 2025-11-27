from app.db.database import Base
from sqlalchemy import Column, Integer, String
from sqlalchemy import Enum as SAEnum

from app.enums.chat_step import ChatStep
from app.enums.license_status import LicenseStatus
from app.enums.license_type import LicenseType
from app.enums.vehicle_step import VehicleStep

class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)

    # to track flow:
    current_step = Column(SAEnum(ChatStep), nullable=False)
    vehicle_step = Column(SAEnum(VehicleStep), nullable=True)

    zip_code = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    license_type = Column(SAEnum(LicenseType), nullable=True)
    license_status = Column(SAEnum(LicenseStatus), nullable=True)