from enum import Enum

class VehicleStep(str, Enum):
    # sub steps of vehicle
    vin = "vin"
    use = "use"
    blind_spot = "blind_spot"

    # commuting
    commuting_days = "commuting_days"
    commuting_miles = "commuting_miles"

    # commercial, farming, business
    annual_mileage = "annual_mileage"