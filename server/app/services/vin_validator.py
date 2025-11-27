import requests
from typing import Dict, Optional

def validate_vehicle_info(year: int, make: str, body_type: str) -> Dict[str, any]:
    try:
        url = f"https://vpic.nhtsa.dot.gov/api/vehicles/GetAllMakes?format=json"
        response = requests.get(url, timeout=5)
        
        if response.status_code != 200:
            return {
                "valid": False,
                "error": "Unable to validate."
            }
        
        data = response.json()
        makes = data.get("Results", [])
        
        make_found = None
        make_id = None
        for m in makes:
            if m.get("Make_Name", "").lower() == make.lower():
                make_found = m.get("Make_Name")
                make_id = m.get("Make_ID")
                break
        
        if not make_found:
            return {
                "valid": False,
                "error": f"Make '{make}' not found in NHTSA database. Please check the spelling and try again."
            }

        if not body_type or not body_type.strip():
            return {
                "valid": False,
                "error": "Body type is required."
            }
        
        return {
            "valid": True,
            "make": make_found,
            "body_type": body_type.strip(),
            "year": str(year)
        }
        
    except Exception as e:
        pass
        import traceback
        traceback.print_exc()
        return {
            "valid": False,
            "error": f"Unable to validate vehicle information at this time. Please try again later. Error: {str(e)}"
        }

def validate_vin(vin: str) -> Dict[str, any]:
    vin = vin.strip().upper()

    if len(vin) != 17: # check length of vin
        return {
            "valid": False,
            "error": f"VIN must be exactly 17 characters."
        }

    try:
        url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"
        response = requests.get(url, timeout=5)
        
        if response.status_code != 200:
            return {
                "valid": False,
                "error": "Unable to validate VIN."
            }
        
        data = response.json()
        results = data.get("Results", [])
        
        if not results:
            return {
                "valid": False,
                "error": "VIN invalid."
            }
        
        make = None
        body_type = None
        year = None
        
        for result in results:
            variable = result.get("Variable")
            value = result.get("Value")
            
            if variable == "Make":
                make = value
            elif variable == "Body Class":
                body_type = value
            elif variable == "Model Year":
                year = value
        
        if not make or make == "NULL":
            return {
                "valid": False,
                "error": "VIN invalid."
            }
        
        return {
            "valid": True,
            "make": make,
            "body_type": body_type or "Unknown",
            "year": year or "Unknown"
        }
    except Exception as e:
        pass
        import traceback
        traceback.print_exc()
        return {
            "valid": False,
            "error": f"Unable to validate VIN at this time. Please try again later. Error: {str(e)}"
        }

