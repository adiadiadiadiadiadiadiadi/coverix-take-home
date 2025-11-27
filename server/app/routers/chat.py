from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import requests

from app.db.database import get_db
from app.db.database import engine
from app.schemas.message import MessageCreate, MessageResponse
from app.services.session import create_session
from app.enums.sender import Sender
from app.enums.chat_step import ChatStep
from app.enums.vehicle_step import VehicleStep
from app.enums.license_type import LicenseType
from app.enums.license_status import LicenseStatus
from app.enums.vehicle_use import VehicleUse
from app.models.session import Session as SessionModel
from app.models.vehicle import Vehicle
from app.models.message import Message
from app.services import messaging as message_service
from app.services import session as session_service
from app.services import vehicle as vehicle_service

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

def get_session_summary(session_id: int, db: Session) -> str:
    """Get a formatted summary of all session data for agent handoff"""
    session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if not session:
        return "No session data available."
    
    summary_parts = []
    summary_parts.append("=== SESSION DATA SUMMARY ===")
    summary_parts.append(f"Session ID: {session_id}")
    
    if session.zip_code:
        summary_parts.append(f"Zip Code: {session.zip_code}")
    if session.full_name:
        summary_parts.append(f"Full Name: {session.full_name}")
    if session.email:
        summary_parts.append(f"Email: {session.email}")
    if session.license_type:
        summary_parts.append(f"License Type: {session.license_type.value}")
    if session.license_status:
        summary_parts.append(f"License Status: {session.license_status.value}")
    
    vehicles = db.query(Vehicle).filter(Vehicle.session_id == session_id).all()
    if vehicles:
        summary_parts.append(f"\nVehicles ({len(vehicles)}):")
        for idx, vehicle in enumerate(vehicles, 1):
            vehicle_parts = []
            if vehicle.vin:
                vehicle_parts.append(f"VIN: {vehicle.vin}")
            if vehicle.year and vehicle.make and vehicle.body_type:
                vehicle_parts.append(f"Vehicle: {vehicle.year} {vehicle.make} {vehicle.body_type}")
            elif vehicle.year and vehicle.make:
                vehicle_parts.append(f"Vehicle: {vehicle.year} {vehicle.make}")
            if vehicle.vehicle_use:
                vehicle_parts.append(f"Use: {vehicle.vehicle_use.value}")
            if vehicle.blind_spot_warning_equipped is not None:
                vehicle_parts.append(f"Blind Spot Warning: {'Yes' if vehicle.blind_spot_warning_equipped else 'No'}")
            if vehicle.days_per_week:
                vehicle_parts.append(f"Commuting Days/Week: {vehicle.days_per_week}")
            if vehicle.one_way_miles:
                vehicle_parts.append(f"One-way Miles: {vehicle.one_way_miles}")
            if vehicle.annual_mileage:
                vehicle_parts.append(f"Annual Mileage: {vehicle.annual_mileage}")
            
            if vehicle_parts:
                summary_parts.append(f"  Vehicle {idx}: " + ", ".join(vehicle_parts))
    
    return "\n".join(summary_parts)

@router.post("/{session_id}/bot/new", response_model=MessageResponse)
def add_bot_message(
    session_id: int,
    db: Session = Depends(get_db),
):
    session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    
    if session and session.license_status and session.current_step == ChatStep.license_status:
        pass
    if session and session.current_step in [ChatStep.license_type, ChatStep.license_status]:
        pass
    
    if session and session.current_step == ChatStep.vehicles and session.vehicle_step is None:
        existing_vehicles = db.query(Vehicle).filter(Vehicle.session_id == session_id).count()
        if existing_vehicles > 0:
            last_user_msg = db.query(Message).filter(
                Message.session_id == session_id,
                Message.sender == Sender.user
            ).order_by(Message.message_id.desc()).first()
            if last_user_msg:
                user_content_lower = last_user_msg.content.lower().strip()
                if user_content_lower in ["no", "n", "nah", "nope"] or (user_content_lower.startswith("no") and "yes" not in user_content_lower):
                    session_service.save(session_id, db, "current_step", ChatStep.license_type)
                    session_service.save(session_id, db, "vehicle_step", None)
                    return add_bot_message(session_id, db)
    
    try:
        content = message_service.get_bot_response(session_id, db)
        if not content:
            content = json.dumps({
                "content": "I encountered an error with your request. Please try again momentarily.",
                "valid": False,
                "extracted": "none"
            })
    except Exception as e:
        content = json.dumps({
            "content": "I encountered an error with your request. Please try again momentarily.",
            "valid": False,
            "extracted": "none"
        })
    
    try:
        json_content = content.strip()
        if json_content.startswith("```"):
            json_content = json_content.split("```")[1]
            if json_content.startswith("json"):
                json_content = json_content[4:]
        json_content = json_content.strip()
        
        try:
            parsed = json.loads(json_content)
        except Exception as e:
            message = message_service.add_message(session_id, Sender.bot, content, db)
            return message
        
        extracted = parsed.get("extracted")
        valid = parsed.get("valid")
        
        if session and session.current_step == ChatStep.vehicles and session.vehicle_step is None:
            all_bot_messages = db.query(Message).filter(
                Message.session_id == session_id,
                Message.sender == Sender.bot
            ).order_by(Message.message_id).all()
            
            user_answered_yes = False
            
            for bot_msg in all_bot_messages:
                content_lower = bot_msg.content.lower()
                if "add a vehicle" in content_lower or "would you like to add" in content_lower:
                    user_msgs_after = db.query(Message).filter(
                        Message.session_id == session_id,
                        Message.sender == Sender.user,
                        Message.message_id > bot_msg.message_id
                    ).order_by(Message.message_id).all()
                    
                    for user_msg in user_msgs_after:
                        user_content_lower = user_msg.content.lower().strip()
                        if user_content_lower in ["yes", "y", "yeah", "yea", "sure", "ok", "okay", "yep"] or (user_content_lower.startswith("yes") and "no" not in user_content_lower):
                            user_answered_yes = True
                            extracted = "true"
                            valid = True
                            session_service.save(session_id, db, "vehicle_step", VehicleStep.vin_or_year_make_body)
                            return add_bot_message(session_id, db)
                    if user_answered_yes:
                        break
            
            if not user_answered_yes:
                last_user_msg = db.query(Message).filter(
                Message.session_id == session_id,
                Message.sender == Sender.user
            ).order_by(Message.message_id.desc()).first()
            
            if last_user_msg:
                user_content_lower = last_user_msg.content.lower().strip()
                
                if user_content_lower in ["no", "n", "nah", "nope"] or (user_content_lower.startswith("no") and "yes" not in user_content_lower):
                    extracted = "false"
                    valid = True
                elif user_content_lower in ["yes", "y", "yeah", "yea", "sure", "ok", "okay", "yep"] or (user_content_lower.startswith("yes") and "no" not in user_content_lower):
                    extracted = "true"
                    valid = True
        
        if session and session.current_step == ChatStep.license_type:
            last_user_msg = db.query(Message).filter(
                Message.session_id == session_id,
                Message.sender == Sender.user
            ).order_by(Message.message_id.desc()).first()
            
            if last_user_msg:
                user_content_lower = last_user_msg.content.lower().strip()
                user_content_clean = user_content_lower.rstrip('?.,!').strip()
                user_has_personal = "personal" in user_content_lower
                user_has_commercial = "commercial" in user_content_lower
                user_has_foreign = "foreign" in user_content_lower
                
                if (user_content_clean == "personal" or 
                    user_content_lower.startswith("personal") or 
                    (user_has_personal and not user_has_commercial and not user_has_foreign)):
                    extracted = "personal"
                    valid = True
                elif (user_content_clean == "commercial" or 
                      user_content_lower.startswith("commercial") or 
                      (user_has_commercial and not user_has_personal and not user_has_foreign)):
                    extracted = "commercial"
                    valid = True
                elif (user_content_clean == "foreign" or 
                      user_content_lower.startswith("foreign") or 
                      (user_has_foreign and not user_has_personal and not user_has_commercial)):
                    extracted = "foreign"
                    valid = True
        
        if session and session.current_step == ChatStep.license_status:
            if session.license_status:
                valid = False
                extracted = "none"
            else:
                last_user_msg = db.query(Message).filter(
                    Message.session_id == session_id,
                    Message.sender == Sender.user
                ).order_by(Message.message_id.desc()).first()
                
                if last_user_msg:
                    user_content_lower = last_user_msg.content.lower().strip()
                    
                    if user_content_lower == "valid" or (user_content_lower.startswith("valid") and "suspended" not in user_content_lower):
                        extracted = "valid"
                        valid = True
                    elif user_content_lower == "suspended" or "suspended" in user_content_lower:
                        extracted = "suspended"
                        valid = True
        
        if session and session.current_step == ChatStep.vehicles and session.vehicle_step == VehicleStep.vin_or_year_make_body:
            last_user_msg = db.query(Message).filter(
                Message.session_id == session_id,
                Message.sender == Sender.user
            ).order_by(Message.message_id.desc()).first()
            
            if last_user_msg:
                user_content = last_user_msg.content
                import re
                body_types_list = ['sedan', 'suv', 'truck', 'coupe', 'hatchback', 'wagon', 'van', 'convertible', 'pickup', 'minivan', 'sport']
                flexible_pattern = r'\b(19\d{2}|20[0-2]\d)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+([A-Za-z]+)'
                matches = list(re.finditer(flexible_pattern, user_content, re.IGNORECASE))
                
                for match in matches:
                    year = match.group(1)
                    make = match.group(2).strip()
                    body_type = match.group(3).strip()
                    
                    if body_type.lower() in body_types_list:
                        extracted = f"{year} {make} {body_type}"
                        valid = True
                        break
                    elif len(user_content.split()) >= 3 and len(body_type) > 2:
                        extracted = f"{year} {make} {body_type}"
                        valid = True
                        break
        if valid and extracted and extracted != "none" and extracted.strip():
            session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
            
            if session.current_step == ChatStep.zip_code:
                session_service.save(session_id, db, "zip_code", extracted)
                session_service.save(session_id, db, "current_step", ChatStep.full_name)
            elif session.current_step == ChatStep.full_name:
                session_service.save(session_id, db, "full_name", extracted)
                session_service.save(session_id, db, "current_step", ChatStep.email)
            elif session.current_step == ChatStep.email:
                session_service.save(session_id, db, "email", extracted)
                session_service.save(session_id, db, "current_step", ChatStep.vehicles)
                session_service.save(session_id, db, "vehicle_step", None)
            elif session.current_step == ChatStep.license_type:
                extracted_lower = extracted.lower().strip() if extracted else ""
                
                if not valid or extracted_lower not in ["personal", "commercial", "foreign"]:
                    last_user_msg = db.query(Message).filter(
                        Message.session_id == session_id,
                        Message.sender == Sender.user
                    ).order_by(Message.message_id.desc()).first()
                    
                    if last_user_msg:
                        user_content_lower = last_user_msg.content.lower().strip()
                        user_content_clean = user_content_lower.rstrip('?.,!').strip()
                        user_has_personal = "personal" in user_content_lower
                        user_has_commercial = "commercial" in user_content_lower
                        user_has_foreign = "foreign" in user_content_lower
                        
                        if user_content_clean in ["personal", "commercial", "foreign"]:
                            extracted_lower = user_content_clean
                            valid = True
                        elif user_content_lower.startswith("personal"):
                            extracted_lower = "personal"
                            valid = True
                        elif user_content_lower.startswith("commercial"):
                            extracted_lower = "commercial"
                            valid = True
                        elif user_content_lower.startswith("foreign"):
                            extracted_lower = "foreign"
                            valid = True
                        elif user_has_personal and not user_has_commercial and not user_has_foreign:
                            extracted_lower = "personal"
                            valid = True
                        elif user_has_commercial and not user_has_personal and not user_has_foreign:
                            extracted_lower = "commercial"
                            valid = True
                        elif user_has_foreign and not user_has_personal and not user_has_commercial:
                            extracted_lower = "foreign"
                            valid = True
                
                if extracted_lower in ["personal", "commercial", "foreign"] and valid:
                    try:
                        license_type_enum = LicenseType(extracted_lower)
                        session.license_type = license_type_enum
                        session.current_step = ChatStep.license_status
                        db.commit()
                        db.refresh(session)
                        return add_bot_message(session_id, db)
                    except ValueError:
                        pass
            elif session.current_step == ChatStep.license_status:
                if session.license_status:
                    pass
                else:
                    extracted_lower = extracted.lower().strip() if extracted else ""
                    
                    if not valid or extracted_lower not in ["valid", "suspended"]:
                        last_user_msg = db.query(Message).filter(
                            Message.session_id == session_id,
                            Message.sender == Sender.user
                        ).order_by(Message.message_id.desc()).first()
                        
                        if last_user_msg:
                            user_content_lower = last_user_msg.content.lower().strip()
                            
                            if user_content_lower == "valid" or (user_content_lower.startswith("valid") and "suspended" not in user_content_lower):
                                extracted_lower = "valid"
                                valid = True
                            elif user_content_lower == "suspended" or "suspended" in user_content_lower:
                                extracted_lower = "suspended"
                                valid = True
                    
                    if extracted_lower in ["valid", "suspended"] and valid:
                        try:
                            license_status_enum = LicenseStatus(extracted_lower)
                            session.license_status = license_status_enum
                            db.commit()
                            db.refresh(session)
                            return add_bot_message(session_id, db)
                        except ValueError:
                            pass
            
            session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
            
            if session.current_step == ChatStep.vehicles:
                if session.vehicle_step is None:
                    extracted_lower = extracted.lower().strip() if extracted else ""
                    
                    if not valid or extracted_lower not in ["true", "false"]:
                        last_user_msg = db.query(Message).filter(
                            Message.session_id == session_id,
                            Message.sender == Sender.user
                        ).order_by(Message.message_id.desc()).first()
                        
                        if last_user_msg:
                            user_content_lower = last_user_msg.content.lower().strip()
                            
                            if user_content_lower in ["no", "n", "nah", "nope"] or (user_content_lower.startswith("no") and "yes" not in user_content_lower):
                                extracted_lower = "false"
                                valid = True
                            elif user_content_lower in ["yes", "y", "yeah", "yea", "sure", "ok", "okay", "yep"] or (user_content_lower.startswith("yes") and "no" not in user_content_lower):
                                extracted_lower = "true"
                                valid = True
                    
                    if extracted_lower == "true" and valid:
                        session_service.save(session_id, db, "vehicle_step", VehicleStep.vin_or_year_make_body)
                        return add_bot_message(session_id, db)
                    elif extracted_lower == "false" and valid:
                        existing_vehicles = db.query(Vehicle).filter(Vehicle.session_id == session_id).count()
                        session_service.save(session_id, db, "current_step", ChatStep.license_type)
                        session_service.save(session_id, db, "vehicle_step", None)
                        return add_bot_message(session_id, db)
                elif session.vehicle_step:
                    vehicle = db.query(Vehicle).filter(Vehicle.session_id == session_id).order_by(Vehicle.vehicle_id.desc()).first()
                    if not vehicle:
                        vehicle = vehicle_service.create_vehicle(db, session_id)
                    
                    if session.vehicle_step == VehicleStep.vin_or_year_make_body:
                        if len(extracted) == 17 and extracted.replace("-", "").replace(" ", "").isalnum():
                            vehicle_service.save(vehicle.vehicle_id, db, "vin", extracted)
                        else:
                            parts = extracted.split()
                            if len(parts) >= 3:
                                try:
                                    vehicle_service.save(vehicle.vehicle_id, db, "year", int(parts[0]))
                                    vehicle_service.save(vehicle.vehicle_id, db, "make", parts[1])
                                    body_type = " ".join(parts[2:]).strip()
                                    if body_type:
                                        vehicle_service.save(vehicle.vehicle_id, db, "body_type", body_type)
                                except Exception:
                                    pass
                        session_service.save(session_id, db, "vehicle_step", VehicleStep.use)
                    elif session.vehicle_step == VehicleStep.use:
                        try:
                            vehicle_use_enum = VehicleUse(extracted.lower().strip())
                            vehicle_service.save(vehicle.vehicle_id, db, "vehicle_use", vehicle_use_enum)
                            if extracted.lower().strip() == "commuting":
                                session_service.save(session_id, db, "vehicle_step", VehicleStep.commuting_days)
                            else:
                                session_service.save(session_id, db, "vehicle_step", VehicleStep.annual_mileage)
                        except ValueError:
                            pass
                    elif session.vehicle_step == VehicleStep.blind_spot:
                        vehicle_service.save(vehicle.vehicle_id, db, "blind_spot_warning_equipped", extracted.lower().strip() == "true")
                        session_service.save(session_id, db, "vehicle_step", None)
                        session_service.save(session_id, db, "current_step", ChatStep.vehicles)
                    elif session.vehicle_step == VehicleStep.commuting_days:
                        vehicle_service.save(vehicle.vehicle_id, db, "days_per_week", int(extracted))
                        session_service.save(session_id, db, "vehicle_step", VehicleStep.commuting_miles)
                    elif session.vehicle_step == VehicleStep.commuting_miles:
                        vehicle_service.save(vehicle.vehicle_id, db, "one_way_miles", int(extracted))
                        session_service.save(session_id, db, "vehicle_step", VehicleStep.blind_spot)
                    elif session.vehicle_step == VehicleStep.annual_mileage:
                        vehicle_service.save(vehicle.vehicle_id, db, "annual_mileage", int(extracted))
                        session_service.save(session_id, db, "vehicle_step", VehicleStep.blind_spot)
    except Exception:
        pass
    
    try:
        message = message_service.add_message(session_id, Sender.bot, content, db)
        return message
    except Exception:
        return None

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