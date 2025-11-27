from enum import Enum

class ChatStep(str, Enum):
    zip_code = "zip_code"
    full_name = "full_name"
    email = "email"
    vehicles = "vehicles"
    license_type = "license_type"
    license_status = "license_status"