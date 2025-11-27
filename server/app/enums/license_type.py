from enum import Enum

class LicenseType(str, Enum):
    foreign="foreign"
    personal="personal"
    commercial="commercial"