from enum import Enum

class VehicleUse(str, Enum):
    commuting="commuting"
    commercial="commercial"
    farming="farming"
    business="business"