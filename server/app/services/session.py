from typing import Optional
from sqlalchemy.orm import Session
from app.models.session import Session as SessionModel
from app.models.message import Message
from app.enums.chat_step import ChatStep
from app.enums.sender import Sender

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