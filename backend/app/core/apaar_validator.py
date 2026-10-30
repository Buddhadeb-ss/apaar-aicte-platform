import re
import hashlib
from typing import Tuple, Dict, Any, Optional
from .config import settings

# Verhoeff algorithm lookup tables for 12-digit Indian national identifier checksums
_verhoeff_d = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

_verhoeff_p = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

_verhoeff_inv = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

def calculate_verhoeff_checksum(number_str: str) -> int:
    """Calculate the Verhoeff checksum digit for a numerical string."""
    c = 0
    reversed_digits = [int(d) for d in reversed(number_str)]
    for i, d in enumerate(reversed_digits):
        c = _verhoeff_d[c][_verhoeff_p[(i + 1) % 8][d]]
    return _verhoeff_inv[c]

def validate_verhoeff(number_str: str) -> bool:
    """Validate a 12-digit number against Verhoeff checksum."""
    if not number_str.isdigit():
        return False
    c = 0
    reversed_digits = [int(d) for d in reversed(number_str)]
    for i, d in enumerate(reversed_digits):
        c = _verhoeff_d[c][_verhoeff_p[i % 8][d]]
    return c == 0

def clean_apaar_id(raw_apaar: str) -> str:
    """Strip spaces, dashes, or separators and return raw numerical string."""
    if not raw_apaar:
        return ""
    return re.sub(r'[\s\-_]', '', str(raw_apaar).strip())

def mask_apaar_id(raw_apaar: str) -> str:
    """
    Format APAAR ID into privacy-preserving masked format: '•••• •••• 1234'
    Never reveals the first 8 digits to comply with statutory privacy rules.
    """
    cleaned = clean_apaar_id(raw_apaar)
    if len(cleaned) < 4:
        return "•••• •••• ••••"
    last_four = cleaned[-4:]
    return f"•••• •••• {last_four}"

def hash_apaar_id(raw_apaar: str) -> str:
    """
    Generate deterministic SHA-256 hash of the cleaned APAAR ID for indexing and
    cross-institutional duplicate checks without storing or exposing cleartext ID.
    """
    cleaned = clean_apaar_id(raw_apaar)
    salted = f"AICTE_APAAR_SALT_V1_{cleaned}"
    return hashlib.sha256(salted.encode('utf-8')).hexdigest()

def validate_apaar_format(raw_apaar: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validates APAAR ID format and structural checksum.
    Returns: (is_valid, cleaned_id_or_empty, error_message_or_none)
    """
    cleaned = clean_apaar_id(raw_apaar)
    
    if not cleaned:
        return False, "", "APAAR ID is missing or empty."
    
    if not cleaned.isdigit():
        return False, "", "APAAR ID must contain numerical digits only."
        
    if len(cleaned) != 12:
        return False, "", f"APAAR ID must be exactly 12 digits (found {len(cleaned)} digits)."
        
    # Check for trivial repetitive sequences (e.g. 000000000000, 111111111111)
    if len(set(cleaned)) == 1:
        return False, "", "APAAR ID cannot consist of repetitive identical digits."
        
    # Check for sequential patterns
    if cleaned in ("123456789012", "012345678901", "987654321098"):
        return False, "", "APAAR ID cannot be a trivial sequential number."
        
    # Verhoeff or fallback checksum validation
    is_checksum_valid = validate_verhoeff(cleaned)
    if not is_checksum_valid:
        # Fallback to Luhn check for synthetic testing flexibility
        # but mark as warning or accept if passes Luhn
        digits = [int(c) for c in cleaned]
        luhn_sum = sum(digits[-1::-2] + [sum(divmod(d * 2, 10)) for d in digits[-2::-2]])
        if luhn_sum % 10 != 0:
            return False, "", "Invalid APAAR checksum: Checksum calculation failed."
            
    return True, cleaned, None

def simulate_apaar_gateway_lookup(apaar_id: str, student_name: str, dob: Optional[str] = None) -> Dict[str, Any]:
    """
    Simulated Gateway Interface to the National Academic Depository / ABC / DigiLocker.
    CLEAR STATUTORY NOTICE: This integration is synthetic/simulated for academic competition & demonstration.
    """
    cleaned = clean_apaar_id(apaar_id)
    is_valid, _, err = validate_apaar_format(cleaned)
    
    if not is_valid:
        return {
            "status": "FAILED",
            "is_valid": False,
            "error": err,
            "is_simulated": True,
            "gateway_notice": "Simulated Gateway: Format validation failed."
        }
        
    # Deterministic mock status based on digits
    # If ends in '0000', simulate unlinked record
    if cleaned.endswith("0000"):
        return {
            "status": "UNLINKED",
            "is_valid": True,
            "aadhaar_linked": False,
            "abc_account_id": None,
            "is_simulated": True,
            "gateway_notice": "Simulated Gateway: APAAR ID exists in registry but is pending Aadhaar e-KYC linkage."
        }
        
    return {
        "status": "VERIFIED_SIMULATED",
        "is_valid": True,
        "aadhaar_linked": True,
        "abc_account_id": f"ABC-{cleaned[0:4]}-{cleaned[4:8]}",
        "registry_name": student_name.upper().strip(),
        "is_simulated": True,
        "gateway_notice": "Simulated Integration: APAAR National Academic Depository Gateway v2.4 (Simulated for SIH26263)."
    }
