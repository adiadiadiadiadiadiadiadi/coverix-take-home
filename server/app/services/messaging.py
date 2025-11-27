from sqlalchemy.orm import Session
from app.models.session import Session as SessionModel
from app.models.message import Message
from app.enums.sender import Sender
from app.enums.vehicle_step import VehicleStep
from app.services.openai_client import client
from app.services.vin_validator import validate_vin, validate_vehicle_info
from sqlalchemy import and_
import json
import requests

# Define the VIN validation tool for GPT
VIN_VALIDATION_TOOL = {
    "type": "function",
    "function": {
        "name": "validate_vin",
        "description": "Validates a Vehicle Identification Number (VIN) against the NHTSA database. Use this when the user provides a VIN to check if it's valid before accepting it. If the VIN is invalid, you should immediately inform the user in your response.",
        "parameters": {
            "type": "object",
            "properties": {
                "vin": {
                    "type": "string",
                    "description": "The 17-character Vehicle Identification Number to validate"
                }
            },
            "required": ["vin"]
        }
    }
}

# Define the vehicle info validation tool for GPT
VEHICLE_INFO_VALIDATION_TOOL = {
    "type": "function",
    "function": {
        "name": "validate_vehicle_info",
        "description": "Validates vehicle information (year, make, body type) against the NHTSA database. Use this when the user provides Year, Make, and Body Type (e.g., '2019 Ford Sedan') to check if it's a valid vehicle combination before accepting it. If invalid, you should immediately inform the user why it's invalid.",
        "parameters": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "The vehicle year (e.g., 2019)"
                },
                "make": {
                    "type": "string",
                    "description": "The vehicle make (e.g., 'Ford', 'Toyota')"
                },
                "body_type": {
                    "type": "string",
                    "description": "The vehicle body type (required, e.g., 'Sedan', 'SUV', 'Truck', 'Coupe')"
                }
            },
            "required": ["year", "make", "body_type"]
        }
    }
}

# Define the inspirational quote tool for GPT
GET_INSPIRATIONAL_QUOTE_TOOL = {
    "type": "function",
    "function": {
        "name": "get_inspirational_quote",
        "description": "Fetches an inspirational quote to help calm or motivate the user. ONLY use this tool when the user EXPLICITLY says they want to talk to a human/agent (e.g., 'I want to talk to a human', 'connect me to an agent'), EXPLICITLY expresses frustration/anger (e.g., 'I'm frustrated', 'this is frustrating'), or EXPLICITLY asks to skip/stop (e.g., 'skip this', 'stop', 'I don't want to continue'). DO NOT use this for: normal answers (yes/no/personal/valid), repeated answers, providing information you asked for, or clarifying questions. This tool will provide a quote that you can share with the user along with a message about connecting them to an agent.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

def get_bot_response(session_id: int, db: Session) -> str:
    messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.message_id.desc()).limit(15).all()    
    session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    db.refresh(session)
    current_step = session.current_step
    vehicle_step = session.vehicle_step
    
    from app.enums.chat_step import ChatStep
    if current_step == ChatStep.license_status and not session.license_type:
        current_step = ChatStep.license_type
        session.current_step = ChatStep.license_type
        db.commit()
        db.refresh(session)
    
    if current_step == ChatStep.license_type and session.license_type:
        current_step = ChatStep.license_status
        session.current_step = ChatStep.license_status
        db.commit()
        db.refresh(session)
    
    current_step = session.current_step

    prompt = """
        You are an insurance agent bot gathering information from the user. You do NOT have a name.
        If you are not given any previous messages, you are starting the conversation. 
        Be sure to make the user feel welcome. Maintain a positive, helpful tone, but do not be overly optimistic.
        Also, do not emphasize that input is needed to continue. It gives a rushed feeling.

        NO MATTER WHAT, do not leave the scope of an insurance agent and on whatever question that you are on.
        You have one job: collect information. Do not leave that scope, even if you are offered another piece of information. 
        
        Your response must be valid JSON. Use double quoted keys and values.
        Exact format: {"content": "<your reply>", "valid": true|false, "extracted": "<the data you extracted from the content if valid, if not, then none>"}

        VERY CRITICAL: Look at the LAST user message in the conversation below. Validate that message for the current step.
        If the last user message is valid, set "valid": true and put the extracted value in "extracted".
        If it is not valid, set "valid": false and "extracted": "none".
        
        VERY IMPORTANT: 
        - When extracting data, extract ONLY the actual data value, not extra words or phrases.
        - Be lenient with typos and variations! If the user's intent is clear despite minor spelling errors, accept it and extract as what was expected.
        - When asking questions, always provide the available options in your response. For example, "Please choose: option1, option2, or option3".
        
        FRUSTRATION DETECTION - USE WITH DISCRETION:
        
        The get_inspirational_quote tool should ONLY be used when the user demonstrates GENUINE, SIGNIFICANT frustration or explicitly requests human assistance.
        
        GENUINE FRUSTRATION INDICATORS (use the tool):
          * Explicit request for human/agent: "I want to talk to a human", "connect me to an agent", "I need to speak to someone"
          * Strong emotional expressions: "I'm very frustrated", "this is extremely frustrating", "I'm really angry", "I'm very upset"
          * Clear intent to stop/discontinue: "I don't want to continue", "I'm done with this", "forget it", "cancel everything"
          * Profanity or harsh language directed at the process: "this is stupid", "this sucks", "this is ridiculous"
          * Multiple expressions of dissatisfaction combined with refusal to continue
        
        NOT FRUSTRATION - DO NOT use the tool for:
          * Normal information provision: If you asked for their name and they say "John Smith" - that's a NORMAL answer, NOT frustration
          * If you asked for email and they provide an email - that's NORMAL, NOT frustration
          * If you asked for zip code and they provide a zip code - that's NORMAL, NOT frustration
          * Light expressions: "im pretty frustrated" without context of wanting to stop is NOT enough - they're still engaging
          * Minor annoyance: "this is annoying" by itself is NOT enough - they need to express intent to stop or request human help
          * Clarifying questions or confusion: "what do you mean?" or "I'm not sure" - these are normal, NOT frustration
          * Repeating answers: If they say "yes" twice, that's normal, NOT frustration
          * Question marks in responses: "personal?" is still a valid answer, NOT frustration
          * Any response that looks like requested information (names, emails, zip codes, vehicle info, license types, etc.)
        
        CRITICAL JUDGMENT RULE:
        - If the user's message could reasonably be an answer to your question (name, email, zip, yes/no, personal/commercial, valid/suspended, vehicle info), 
          it is NOT frustration - extract the information normally.
        - Only use the tool if the user's PRIMARY intent is to express strong frustration AND either request human help OR stop the process entirely.
        - Light frustration while still engaging ("im pretty frustrated" but then continues answering) is NOT enough - continue collecting information.
        - When in doubt, DO NOT use the tool. Continue with normal information collection.
        
        After using the tool, acknowledge their frustration, share the inspirational quote, and let them know you're connecting them to an agent.
        Set valid: true, extracted: "connect_to_agent" when this happens.

        Past 15 Messages (in chronological order, oldest first):

        *** CONVERSATION BEGINS ******

        
        """
    for m in reversed(messages):
        prompt = prompt + m.sender + ": " + m.content + "\n"
    
    prompt = prompt + "**** CONVERSATION ENDS ***** \n"
    
    if not messages:
        prompt += "If the conversation has no messages, treat this message as an intro."

    match current_step:
        case "zip_code":
            prompt += """
            Current step: ZIP CODE. Validate the LAST user message. if it's a valid 5-digit zip code, 
            set valid: true and extracted: just the zip code (e.g., '95014'). If valid, acknowledge and ask for their full name. 
            If invalid, set valid: false and ask for a valid 5-digit zip code.
            """
        case "full_name":
            prompt += """
            Current step: FULL NAME. Validate the LAST user message. if it contains a name (first and last name), 
            set valid: true and extracted: the full name. If valid, acknowledge and ask for their email address. 
            If invalid, set valid: false and ask for their full name.
            """
        case "email":
            prompt += """
            Current step: EMAIL. Validate the LAST user message. if it's a valid email address, 
            set valid: true and extracted: the email. If valid, acknowledge and ask if they would
            like to add a vehicle. 
            If invalid, set valid: false and ask for a valid email address.
            """
        case "license_type":
            already_collected = session.license_type is not None
            license_type_value = session.license_type.value if session.license_type else None
            
            prompt += f"""
            Current step: LICENSE TYPE. This is AFTER the vehicle question - the user has already answered whether they want to add a vehicle.
            DO NOT ask about vehicles again. DO NOT ask for VIN or vehicle information. We are ONLY asking for license type now.
            
            {"CRITICAL: License type has ALREADY been collected: " + license_type_value + ". This should not happen. Move to license_status step." if already_collected else ""}
            
            The available options are: personal, commercial, or foreign. 
            In your response, always show these options: 'Please choose your license type: personal, commercial, or foreign.' 
            Validate the LAST user message - be lenient with typos. If it matches one of the options (accounting for typos), set 
            valid: true and extracted: exactly one of these values (personal, commercial, or foreign) - normalize any typos to the 
            correct value. If valid, acknowledge and ask for their license status WHICH SHOULD ONLY BE VALID OR SUSPENDED. 
            If invalid, set valid: false and ask again with the options clearly shown.
            
            REMEMBER: We are past the vehicle step. DO NOT mention vehicles, VIN, or vehicle information in your response.
            DO NOT backtrack to vehicle questions."""
        case "license_status":
            if session.license_status:
                session_summary_parts = []
                if session.zip_code:
                    session_summary_parts.append(f"Zip Code: {session.zip_code}")
                if session.full_name:
                    session_summary_parts.append(f"Full Name: {session.full_name}")
                if session.email:
                    session_summary_parts.append(f"Email: {session.email}")
                if session.license_type:
                    session_summary_parts.append(f"License Type: {session.license_type.value}")
                if session.license_status:
                    session_summary_parts.append(f"License Status: {session.license_status.value}")
                
                from app.models.vehicle import Vehicle
                vehicles = db.query(Vehicle).filter(Vehicle.session_id == session_id).all()
                if vehicles:
                    session_summary_parts.append(f"Vehicles: {len(vehicles)} vehicle(s) added")
                
                session_summary = "\n".join(session_summary_parts) if session_summary_parts else "No additional information collected."
                
                prompt += f"""
                Current step: LICENSE STATUS - COMPLETION MESSAGE.
                
                CRITICAL: The user has ALREADY provided their license status: {session.license_status.value}
                ALL information has been collected. The conversation is COMPLETE.
                
                You MUST:
                1. Acknowledge that all information has been collected
                2. Thank the user for their time
                3. Indicate that you're connecting them to an agent who will help them with their insurance needs
                4. Include the following complete session summary in your response. IMPORTANT: Format the summary with each item on a new line for readability:
                
                {session_summary}
                
                5. Set valid: true and extracted: "none" (no more data to extract)
                6. DO NOT ask for any additional information
                7. This is the FINAL message - the conversation is complete
                
                Your response should be a friendly completion message with the session summary.
                Format the summary section with each field on its own line (Zip Code on one line, Full Name on the next line, etc.)
                """
            else:
                session_summary_parts = []
                if session.zip_code:
                    session_summary_parts.append(f"Zip Code: {session.zip_code}")
                if session.full_name:
                    session_summary_parts.append(f"Full Name: {session.full_name}")
                if session.email:
                    session_summary_parts.append(f"Email: {session.email}")
                if session.license_type:
                    session_summary_parts.append(f"License Type: {session.license_type.value}")
                
                from app.models.vehicle import Vehicle
                vehicles = db.query(Vehicle).filter(Vehicle.session_id == session_id).all()
                if vehicles:
                    session_summary_parts.append(f"Vehicles: {len(vehicles)} vehicle(s) added")
                
                session_summary = "\n".join(session_summary_parts) if session_summary_parts else "No additional information collected."
                
                collected_info = []
                if session.zip_code:
                    collected_info.append(f"✓ Zip Code: {session.zip_code}")
                if session.full_name:
                    collected_info.append(f"✓ Full Name: {session.full_name}")
                if session.email:
                    collected_info.append(f"✓ Email: {session.email}")
                if session.license_type:
                    collected_info.append(f"✓ License Type: {session.license_type.value} (ALREADY COLLECTED - DO NOT ASK AGAIN)")
                collected_info_str = "\n".join(collected_info) if collected_info else "No information collected yet."
                
                prompt += f"""
                Current step: LICENSE STATUS. THIS IS THE FINAL STEP. AFTER THIS, THE CONVERSATION IS COMPLETE.
                
                INFORMATION ALREADY COLLECTED (DO NOT ASK ABOUT THESE AGAIN):
                {collected_info_str}
                
                CRITICAL - ABSOLUTE REQUIREMENTS - NO EXCEPTIONS:
                1. We are PAST the vehicle step. DO NOT ask about vehicles, VIN, Year/Make/Body Type, or adding vehicles.
                2. We are PAST the license_type step. The user has ALREADY provided their license type: {session.license_type.value if session.license_type else 'N/A'}. 
                   DO NOT ask about license type again. DO NOT ask "Please choose your license type" or any variation.
                   DO NOT backtrack to license type questions. The license type is ALREADY COLLECTED.
                3. We are ONLY asking for LICENSE STATUS now. This is the ONLY question you should ask.
                
                ABSOLUTE REQUIREMENT - NO EXCEPTIONS:
                The ONLY two acceptable values are: "valid" OR "suspended"
                THERE ARE NO OTHER OPTIONS ALLOWED. DO NOT MENTION "EXPIRED". LICENSE STATUSES CAN ONLY INCLUDE "valid" or "suspended"
                
                VERY CRITICAL RULES:
                Look at the VERY LAST message in the conversation that has sender "user". That is the message you must validate.
                
                If the LAST user message contains the word "valid" at all in the string (even if it's part of another word like "validation"),
                you MUST:
                1. Set valid: true (ALWAYS TRUE, NEVER ANYTHING ELSE)
                2. Set extracted: exactly 'valid' (lowercase, no quotes, just the word valid)
                3. Acknowledge their answer briefly
                4. DO NOT ask for license status again - it has been provided
                5. The system will handle generating the completion message
                
                If the LAST user message contains the word "suspended", you MUST:
                1. Set valid: true (NOT false)
                2. Set extracted: exactly 'suspended' (lowercase)
                3. Acknowledge their answer briefly
                4. DO NOT ask for license status again - it has been provided
                5. The system will handle generating the completion message
                
                If the LAST user message does NOT contain "valid" or "suspended", then:
                1. Ask ONLY: "Please choose your license status: valid or suspended."
                2. DO NOT ask about license type, vehicles, or anything else.
                3. Set valid: false and extracted: "none"
                
                REMEMBER: This is the LAST step. After license status is provided, the conversation is COMPLETE. 
                DO NOT ask for date of birth, additional coverage, or ANY other information.
                DO NOT backtrack to previous steps. DO NOT ask about license type - it has already been provided and is shown above.
                """
        case "vehicles":
            if vehicle_step:
                match vehicle_step:
                    case "vin_or_year_make_body":
                        prompt += """
                        Current step: VEHICLE IDENTIFICATION. You need to ask the user for their vehicle information.
                        The user can provide either: (1) A VIN (exactly 17 characters, alphanumeric), OR (2) Year, Make, and Body Type (e.g., '2020 Toyota Sedan' or '2019 Ford Truck').
                        
                        CRITICAL - FIRST MESSAGE: If you have NOT asked for vehicle information yet in this conversation, you MUST ask: 'Please provide either a VIN (17 characters) or Year, Make, and Body Type (e.g., 2020 Toyota Sedan).'
                        
                        CRITICAL RULES - NO EXCEPTIONS:
                        - DO NOT say "I will validate" or "hold on a moment" or "please wait". Validate silently and immediately proceed.
                        - If the user provides a VIN (exactly 17 characters, alphanumeric), you MUST use the validate_vin tool to check if it's valid. After validation, immediately proceed without mentioning validation.
                        - If the user provides Year/Make/Body Type (like "2019 Ford Sedan" or "2020 Toyota SUV"), you MUST use the validate_vehicle_info tool. After validation, immediately proceed without mentioning validation.
                        - ABSOLUTE REQUIREMENT: Body Type is MANDATORY and CANNOT be omitted, skipped, or left empty.
                        - BEFORE calling validate_vehicle_info tool: Check if the user provided a body type. If they only provided "Year Make" (like "2020 Toyota" or "2019 Ford") without a body type, DO NOT call the tool. Instead, set valid: false, extracted: "none", and ask: "Please provide Year, Make, AND Body Type (e.g., '2020 Toyota Sedan' or '2019 Ford Truck'). Body type is required."
                        - IMPORTANT: Extract the year (as integer), make (as string), and body_type (as string, REQUIRED - e.g., "Sedan", "SUV", "Truck", "Coupe", "Hatchback", "Wagon").
                          For "2019 Ford Sedan", extract year=2019, make="Ford", body_type="Sedan".
                          For "2020 Toyota SUV", extract year=2020, make="Toyota", body_type="SUV".
                          If user says "2020 Toyota" without body type, set valid: false and ask for body type.
                        - When calling validate_vehicle_info tool, you MUST provide all three: year, make, AND body_type. The tool will reject if body_type is missing.
                        - If you use a tool and the vehicle info is invalid, set valid: false and immediately inform the user why it's invalid (do not say "I validated" or "I checked" - just state the error directly).
                        - If you use a tool and the vehicle info is valid, set valid: true and extracted: the VIN (if VIN was provided) or 'year make body_type' format (if year/make/body_type was provided, e.g., '2019 Ford Sedan').
                        - If valid, acknowledge briefly (e.g., "Thank you for providing the vehicle details") and immediately ask for vehicle use (commuting, commercial, farming, or business). DO NOT mention validation or checking.
                        - If invalid, set valid: false and ask for either a valid VIN or Year, Make, and Body Type (emphasize that all three are required).
                        """
                    case "use":
                        prompt += "Current step: VEHICLE USE. The available options are: commuting, commercial, farming, or business. In your response, always show these options: 'Please choose the vehicle use: commuting, commercial, farming, or business.' Validate the LAST user message - be lenient with typos. If it matches one of the options (accounting for typos), set valid: true and extracted: exactly one of these values (commuting, commercial, farming, or business) - normalize any typos to the correct value. If valid, acknowledge and ask for the next step based on use type: if commuting, ask ONLY about days per week (do NOT ask about miles yet - that comes next). If commercial/farming/business, ask for annual mileage. If invalid, set valid: false and ask again with the options clearly shown."
                    case "commuting_days":
                        prompt += "Current step: COMMUTING DAYS PER WEEK. This is the FIRST of two separate questions about commuting. Ask ONLY about how many days per week they commute. Do NOT ask about miles yet. Validate the LAST user message - if it's a number between 1-7, set valid: true and extracted: the number. If valid, acknowledge and then ask the SECOND question: 'How many one-way miles is your commute to work or school?' If invalid, set valid: false and ask for a number of days per week between 1-7."
                    case "commuting_miles":
                        prompt += "Current step: COMMUTING MILES (ONE-WAY). This is the SECOND question about commuting. Ask ONLY about one-way miles to work or school. Do NOT ask about days per week (that was already asked). Validate the LAST user message - if it's a positive number, set valid: true and extracted: the number. If valid, acknowledge and ask about blind spot warning (yes/no). If invalid, set valid: false and ask for a valid number of one-way miles."
                    case "annual_mileage":
                        prompt += "Current step: ANNUAL MILEAGE. Validate the LAST user message - if it's a positive number, set valid: true and extracted: the number. If valid, acknowledge and ask about blind spot warning (yes/no). If invalid, set valid: false and ask for a valid number."
                    case "blind_spot":
                        prompt += """
                        Current step: BLIND SPOT WARNING - FINAL STEP FOR THIS VEHICLE.
                        
                        CRITICAL: Look at the conversation history. If you have already asked "Does your vehicle have blind spot warning?" and the user has answered (yes/no/any variation), then:
                        - Do NOT ask the blind spot question again
                        - Acknowledge their previous answer
                        - Immediately ask: 'Would you like to add another vehicle? Please respond with yes or no.'
                        - Set valid: true and extracted: 'true' or 'false' based on their previous answer
                        
                        If you have NOT asked this question yet, ask: 'Does your vehicle have blind spot warning? Please respond with yes or no.'
                        Do NOT mention insurance coverage or adding features. You are simply asking if the vehicle has this feature.
                        
                        Validate the LAST user message - be VERY lenient with variations and typos.
                        - ANY affirmative response (yes, y, ye, yeah, yea, sure, ok, okay, true, correct, absolutely, definitely, yep, yeh, yup, k, sure thing, affirmative, of course) should be considered valid.
                          Set valid: true and extracted: 'true' for ANY affirmative response.
                        - ANY negative response (no, n, nah, nope, false, incorrect, negative, not really) should be considered valid.
                          Set valid: true and extracted: 'false' for ANY negative response.
                        
                        If valid (whether from current answer or previous answer), acknowledge briefly and ask: 'Would you like to add another vehicle? Please respond with yes or no.'
                        Only set valid: false if the response is completely unclear or unrelated.
                        """
            else:
                prompt += """
                Current step: ADD VEHICLE QUESTION. Ask if they want to add a vehicle. Users can add multiple vehicles.
                
                CRITICAL: Check the conversation history CAREFULLY. If the user has already answered "no" to adding a vehicle AND you have already asked about license type, then we are PAST the vehicle step. 
                DO NOT ask about vehicles again if we're past that step. The flow is: vehicles -> license_type -> license_status.
                If you see license type questions in the conversation, we are already past vehicles. DO NOT regress backwards.
                
                CRITICAL: Check the conversation history CAREFULLY. Count how many times you asked "Would you like to add a vehicle?" or any variation. 
                If the user has ALREADY answered "yes" to adding a vehicle (anywhere in the conversation), then:
                - Do NOT ask the question again under ANY circumstances
                - Do NOT repeat the question
                - Acknowledge their previous "yes" answer if this is the first time you're seeing it
                - Immediately ask for vehicle information: 'Please provide either a VIN (17 characters) or Year, Make, and Body Type (e.g., 2020 Toyota Sedan).'
                - Set valid: true and extracted: 'true'
                
                If you have already asked and they answered "no" (or any negative), then:
                - Do NOT ask the question again
                - Do NOT repeat the question
                - Acknowledge their answer
                - Immediately ask for license type: 'Please choose your license type: personal, commercial, or foreign.'
                - Set valid: true and extracted: 'false'
                
                If you have NOT asked this question yet AND the user has NOT answered it, ask: 'Would you like to add a vehicle? Please respond with yes or no.'
                
                REMEMBER: If you see "yes" anywhere in the conversation history about vehicles, treat it as already answered and proceed to asking for vehicle information.
                
                Validate the LAST user message. Be VERY lenient with variations and typos.
                - ANY affirmative response (yes, y, ye, yeah, yea, sure, ok, okay, true, correct, absolutely, 
                  definitely, yep, yeh, yup, k, sure thing, affirmative, of course) should be considered valid.
                  Set valid: true and extracted: 'true' (NOT 'yes', extract as 'true').
                - ANY negative response (no, n, nah, nope, false, incorrect, negative, not really) should be considered valid.
                  Set valid: true and extracted: 'false' (NOT 'no', extract as 'false').
                
                If valid, acknowledge and proceed (if extracted is 'true', ask for VIN or Year/Make/Body Type; 
                if extracted is 'false', ask for license type). 
                Only set valid: false if the response is completely unclear or unrelated.
                """

    messages_list = [{"role": "system", "content": prompt}]
    tools = []
    tools.append(GET_INSPIRATIONAL_QUOTE_TOOL)
    if current_step == "vehicles" and vehicle_step == "vin_or_year_make_body":
        tools.append(VIN_VALIDATION_TOOL)
        tools.append(VEHICLE_INFO_VALIDATION_TOOL)
    
    tools = tools if tools else None
    
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages_list,
        tools=tools,
        tool_choice="auto" if tools else None
    )
    
    message = completion.choices[0].message
    message_dict = {
        "role": message.role,
        "content": message.content
    }
    if message.tool_calls:
        message_dict["tool_calls"] = [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            }
            for tc in message.tool_calls
        ]
    messages_list.append(message_dict)
    
    if message.tool_calls:
        try:
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                try:
                    function_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    continue
                
                if function_name == "validate_vin":
                    try:
                        vin = function_args.get("vin")
                        
                        if not vin:
                            validation_result = {
                                "valid": False,
                                "error": "VIN is required."
                            }
                        else:
                            validation_result = validate_vin(vin)
                        messages_list.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(validation_result)
                        })
                    except Exception:
                        messages_list.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps({
                                "valid": False,
                                "error": f"Error validating VIN: {str(e)}"
                            })
                        })
                elif function_name == "validate_vehicle_info":
                    try:
                        year = function_args.get("year")
                        make = function_args.get("make")
                        body_type = function_args.get("body_type")
                        
                        if not year or not make:
                            validation_result = {
                                "valid": False,
                                "error": "Year and make are required."
                            }
                        elif not body_type or not body_type.strip():
                            validation_result = {
                                "valid": False,
                                "error": "Body type is required. Please provide the vehicle body type (e.g., Sedan, SUV, Truck, Coupe)."
                            }
                        else:
                            validation_result = validate_vehicle_info(year, make, body_type)
                        
                        messages_list.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(validation_result)
                        })
                    except Exception:
                        messages_list.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps({
                                "valid": False,
                                "error": f"Error validating vehicle information: {str(e)}"
                            })
                        })
                elif function_name == "get_inspirational_quote":
                    try:
                        response = requests.get("https://zenquotes.io?api=quotes", timeout=5)
                        
                        if response.status_code == 200:
                            quotes_data = response.json()
                            if quotes_data and len(quotes_data) > 0:
                                quote = quotes_data[0]
                                quote_text = quote.get("q", "")
                                quote_author = quote.get("a", "Unknown")
                                quote_result = {
                                    "quote": quote_text,
                                    "author": quote_author,
                                    "success": True
                                }
                            else:
                                quote_result = {
                                    "quote": "The greatest mistake you can make in life is to be continually fearing you will make one.",
                                    "author": "Elbert Hubbard",
                                    "success": False,
                                    "note": "Fallback quote used"
                                }
                        else:
                            quote_result = {
                                "quote": "The greatest mistake you can make in life is to be continually fearing you will make one.",
                                "author": "Elbert Hubbard",
                                "success": False,
                                "note": "API error, fallback quote used"
                            }
                        
                        messages_list.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(quote_result)
                        })
                    except Exception:
                        messages_list.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps({
                                "quote": "The greatest mistake you can make in life is to be continually fearing you will make one.",
                                "author": "Elbert Hubbard",
                                "success": False,
                                "error": str(e)
                            })
                        })
            
            tool_result_summary = ""
            for tool_call in message.tool_calls:
                try:
                    function_args = json.loads(tool_call.function.arguments)
                    for msg in messages_list:
                        if isinstance(msg, dict) and msg.get("role") == "tool" and msg.get("tool_call_id") == tool_call.id:
                            validation_result = json.loads(msg.get("content", "{}"))
                            
                            if tool_call.function.name == "validate_vin":
                                vin = function_args.get("vin")
                                if validation_result.get("valid"):
                                    tool_result_summary += f"The VIN {vin} is VALID. Vehicle: {validation_result.get('year', 'Unknown')} {validation_result.get('make', 'Unknown')} {validation_result.get('body_type', 'Unknown')}. Set valid: true and extracted: '{vin}'. "
                                else:
                                    tool_result_summary += f"The VIN {vin} is INVALID. Error: {validation_result.get('error', 'Unknown error')}. Set valid: false and extracted: 'none'. Inform the user immediately why the VIN is invalid. "
                            
                            elif tool_call.function.name == "validate_vehicle_info":
                                year = function_args.get("year")
                                make = function_args.get("make")
                                body_type = function_args.get("body_type")
                                vehicle_desc = f"{year} {make} {body_type}"
                                
                                if validation_result.get("valid"):
                                    extracted_value = f"{year} {make} {body_type}"
                                    tool_result_summary += f"The vehicle {vehicle_desc} is VALID. Set valid: true and extracted: '{extracted_value}'. "
                                else:
                                    tool_result_summary += f"The vehicle {vehicle_desc} is INVALID. Error: {validation_result.get('error', 'Unknown error')}. Set valid: false and extracted: 'none'. Inform the user immediately why the vehicle information is invalid. "
                            
                            elif tool_call.function.name == "get_inspirational_quote":
                                quote = validation_result.get("quote", "")
                                author = validation_result.get("author", "Unknown")
                                tool_result_summary += f"An inspirational quote was fetched: '{quote}' by {author}. Share this quote with the user, acknowledge their frustration or request to speak with a human, and let them know you're connecting them to an agent. Set valid: true and extracted: 'connect_to_agent'. "
                            break
                except Exception:
                    if tool_call.function.name == "validate_vin":
                        tool_result_summary += "Error validating VIN. Set valid: false and extracted: 'none'. "
                    elif tool_call.function.name == "validate_vehicle_info":
                        tool_result_summary += "Error validating vehicle information. Set valid: false and extracted: 'none'. "
            
            messages_list.append({
                "role": "system",
                "content": f"Based on the tool result: {tool_result_summary} Now respond in valid JSON format. Use double quoted keys and values. Exact format: {{\"content\": \"<your reply>\", \"valid\": true|false, \"extracted\": \"<the data you extracted from the content if valid, if not, then none>\"}}"
            })
            
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages_list,
                tools=tools,
                tool_choice="none" 
            )
            
            message = completion.choices[0].message
        except Exception:
            return json.dumps({
                "content": "I apologize, but I encountered an error processing your request. Please try again.",
                "valid": False,
                "extracted": "none"
            })
    
    # Ensure we have content
    if not message.content:
        return json.dumps({
            "content": "I apologize, but I encountered an error processing your request. Please try again.",
            "valid": False,
            "extracted": "none"
        })
    
    try:
        content_stripped = message.content.strip()
        if content_stripped.startswith("```"):
            content_stripped = content_stripped.split("```")[1]
            if content_stripped.startswith("json"):
                content_stripped = content_stripped[4:]
        content_stripped = content_stripped.strip()
        json.loads(content_stripped)  # Validate it's JSON
        return message.content
    except json.JSONDecodeError:
        return json.dumps({
            "content": "Error while processing your request. Please try again.",
            "valid": False,
            "extracted": "none"
        })

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