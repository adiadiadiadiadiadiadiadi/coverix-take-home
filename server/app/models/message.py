from database import Base
from sqlalchemy import Column, Integer, String
from sqlalchemy import Enum as SAEnum
from server.app.enums.sender import Sender

class Message(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    session_id = Column(Integer, primary_key=True, nullable=False)
    sender = Column(SAEnum(Sender), nullable=False)
    content = Column(String, nullable=False)