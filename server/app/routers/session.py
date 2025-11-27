from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.schemas.message import MessageCreate, MessageResponse
from app.services.session import create_session
from app.enums.sender import Sender
from app.services import messaging as message_service
from app.services import session as session_service
from app.enums.license_status import LicenseStatus
from app.enums.license_type import LicenseType

router = APIRouter(
    prefix="/session",
    tags=["Session"]
)

@router.post("/save", response_model=None)
def save(
    session_id: int,
    attribute: str,
    value: str | LicenseType | LicenseStatus,
    db: Session = Depends(get_db),
):
    session_service.save(session_id=session_id, db=db, attribute=attribute, value=value)