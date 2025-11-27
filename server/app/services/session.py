from typing import Optional, Any
from sqlalchemy.orm import Session
from app.models.session import Session as SessionModel
from app.models.message import Message
from app.enums.chat_step import ChatStep
from app.enums.vehicle_step import VehicleStep
from app.enums.sender import Sender
from app.enums.license_status import LicenseStatus
from app.enums.license_type import LicenseType

def create_session(db: Session):
    session = SessionModel(
        current_step=ChatStep.zip_code,
        vehicle_step=None
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def add_message(
    session_id: int,
    sender: Sender,
    db: Session,
    content: Optional[str] = None,
):
    message = Message(
        session_id=session_id,
        sender=sender,
        content=content or ""
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message

def save (
    session_id: int,
    db: Session,
    attribute: str,
    value: Any
):
    ses = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    setattr(ses, attribute, value)
    db.commit()
    db.refresh(ses)