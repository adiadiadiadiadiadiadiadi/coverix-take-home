from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services import vehicle as vehicle_service
from app.enums.license_status import LicenseStatus
from app.enums.license_type import LicenseType

router = APIRouter(
    prefix="/vehicle",
    tags=["Vehicles"]
)

@router.post("/save", response_model=None)
def save(
    session_id: int,
    attribute: str,
    value: str | LicenseType | LicenseStatus,
    db: Session = Depends(get_db),
):
    vehicle_service.save(session_id=session_id, db=db, attribute=attribute, value=value)