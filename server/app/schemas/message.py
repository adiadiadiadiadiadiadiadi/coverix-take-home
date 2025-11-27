from pydantic import BaseModel
from app.enums.sender import Sender

class MessageBase(BaseModel):
    session_id: int
    sender: Sender
    content: str

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    message_id: int

    class Config:
        from_attributes = True
