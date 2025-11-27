from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.schemas.message import MessageCreate, MessageResponse
from app.services.session import create_session
from app.enums.sender import Sender
from app.services import messaging as message_service
from app.services import session as session_service

router = APIRouter(
    prefix="/chat",
    tags=["Message"]
)

@router.post("/new", response_model=int)
def create_new_chat(db: Session = Depends(get_db)):
    session = create_session(db)
    return session.session_id

@router.post("/{session_id}/new", response_model=MessageResponse)
def add_message(
    session_id: int,
    content: str = Body(...),
    sender: str = Body(...),
    db: Session = Depends(get_db),
):
    sender_enum = Sender.bot if sender == "bot" else Sender.user
    message = message_service.add_message(session_id, sender_enum, content, db)
    return message

@router.post("/{session_id}/bot/new", response_model=MessageResponse)
def add_bot_message(
    session_id: int,
    db: Session = Depends(get_db),
):
    content = message_service.get_bot_response(session_id, db)
    message = message_service.add_message(session_id, Sender.bot, content, db)
    return message

@router.get("/get-all-messages/{session_id}", response_model=List[MessageResponse])
def get_messages(session_id, db: Session = Depends(get_db)):
    messages = message_service.get_messages(session_id, db)
    return messages

@router.get("/get-num-messages/{session_id}/{sender}", response_model=int)
def get_num_messages(
    session_id: int,
    sender: str,
    db: Session = Depends(get_db)
):
    sender_enum = Sender.bot if sender == 'bot' else Sender.user
    return message_service.get_num_messages(session_id, db, sender_enum)