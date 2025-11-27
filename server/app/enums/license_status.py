from enum import Enum

class LicenseStatus(str, Enum):
    valid = "valid"
    suspended = "suspended"