from enum import Enum

class VehicleStep(str, Enum):
    # sub steps of vehicle
    vin_or_year_make_body = "vin_or_year_make_body"
    use = "use"
    blind_spot = "blind_spot"

    # commuting
    commuting_days = "commuting_days"
    commuting_miles = "commuting_miles"

    # commercial, farming, business
    annual_mileage = "annual_mileage"