from app.db.database import Base
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from app.enums.sender import Sender

class Message(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.session_id"), nullable=False)
    sender = Column(SAEnum(Sender), nullable=False)
    content = Column(String, nullable=False)