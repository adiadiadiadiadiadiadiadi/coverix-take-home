from sqlalchemy.orm import Session
from app.models.session import Session as SessionModel
from app.models.message import Message
from app.enums.sender import Sender
from app.services.openai_client import client
from sqlalchemy import and_

def get_bot_response(session_id: int, db: Session) -> str:
    messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.message_id.desc()).limit(15).all()    
    current_step = db.query(SessionModel).filter(SessionModel.session_id == session_id).first().current_step

    prompt = """
        You are an insurance agent bot gathering information from the user. You do NOT have a name.
        If you are not given any previous messages, you are starting the conversation. 
        Be sure to make the user feel welcome. Maintain a positive, helpful tone, but do not be overly optimistic.
        If the last response was not valid, let the user know and reprompt.

        Your response must be valid JSON. Use double quoted keys and values.
        Exact format: {"content": "<your reply>", "valid": true|false}

        Past 15 Messages:

        *** CONVERSATION BEGINS ******

        
        """
    for m in messages:
        prompt = prompt + m.sender + ": " + m.content + "\n"
    
    prompt = prompt + "**** CONVERSATION ENDS ***** \n if the conversation has no messages, treat this message as an intro."

    match current_step:
        case "zip_code":
            prompt += "The user should now be entering their zip code."
    prompt += "Base your response around that fact."

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt}
        ]
    )

    return completion.choices[0].message.content

def get_messages(session_id: int, db: Session):
    messages = db.query(Message).filter(Message.session_id == session_id).all()
    return messages

def get_num_messages(session_id: int, db: Session, sender: Sender) -> int:
    return (
        db.query(Message)
        .filter(and_(Message.session_id == session_id, Message.sender == sender))
        .count()
    )

def add_message(session_id: int, sender: Sender, content: str, db: Session):
    msg = Message(
        session_id=session_id,
        sender=sender,
        content=content
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg