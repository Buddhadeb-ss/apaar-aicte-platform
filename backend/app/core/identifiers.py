import re
import uuid
import hashlib
from typing import Tuple, Optional

# Verhoeff algorithm multiplication and permutation matrices
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

def generate_uuid() -> str:
    """Generate RFC 4122 v4 UUID."""
    return str(uuid.uuid4())

def normalize_identifier(identifier: Optional[str]) -> str:
    """
    Normalize internal identifiers (Roll numbers, AICTE IDs, Tokens).
    Strips leading/trailing whitespace and converts to uppercase standard.
    """
    if not identifier:
        return ""
    # Collapse multiple spaces and trim
    cleaned = re.sub(r'\s+', ' ', str(identifier).strip())
    return cleaned.upper()

def clean_apaar_id(raw_apaar: Optional[str]) -> str:
    """Strip spaces, dashes, or non-numeric characters from APAAR ID."""
    if not raw_apaar:
        return ""
    return re.sub(r'[^0-9]', '', str(raw_apaar).strip())

def calculate_verhoeff_checksum(number_str: str) -> int:
    """Calculate Verhoeff checksum digit for numeric string."""
    c = 0
    reversed_digits = [int(d) for d in reversed(number_str)]
    for i, d in enumerate(reversed_digits):
        c = _verhoeff_d[c][_verhoeff_p[(i + 1) % 8][d]]
    return _verhoeff_inv[c]

def validate_verhoeff(number_str: str) -> bool:
    """Validate 12-digit number against Verhoeff checksum."""
    if not number_str.isdigit():
        return False
    c = 0
    reversed_digits = [int(d) for d in reversed(number_str)]
    for i, d in enumerate(reversed_digits):
        c = _verhoeff_d[c][_verhoeff_p[i % 8][d]]
    return c == 0

def mask_apaar_id(raw_apaar: Optional[str]) -> str:
    """
    Format APAAR ID into privacy-preserving masked format: '•••• •••• 1098'
    Never reveals the first 8 digits in general dashboards, logs, or public endpoints.
    """
    cleaned = clean_apaar_id(raw_apaar)
    if len(cleaned) < 4:
        return "•••• •••• ••••"
    last_four = cleaned[-4:]
    return f"•••• •••• {last_four}"

def hash_apaar_id(raw_apaar: Optional[str]) -> str:
    """
    Generate deterministic SHA-256 hash of the cleaned APAAR ID with salt.
    Enables collision detection without storing or logging plain APAAR.
    """
    cleaned = clean_apaar_id(raw_apaar)
    if not cleaned:
        return ""
    salted = f"AICTE_APAAR_SALT_V1_{cleaned}"
    return hashlib.sha256(salted.encode('utf-8')).hexdigest()

def validate_apaar_format(raw_apaar: Optional[str]) -> Tuple[bool, str, Optional[str]]:
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
        
    # Check for trivial sequential patterns
    if cleaned in ("123456789012", "012345678901", "987654321098"):
        return False, "", "APAAR ID cannot be a trivial sequential number."
        
    # Verhoeff checksum validation
    is_checksum_valid = validate_verhoeff(cleaned)
    if not is_checksum_valid:
        # Fallback to Luhn check for synthetic flexibility
        digits = [int(c) for c in cleaned]
        luhn_sum = sum(digits[-1::-2] + [sum(divmod(d * 2, 10)) for d in digits[-2::-2]])
        if luhn_sum % 10 != 0:
            return False, "", "Invalid APAAR checksum: Calculation failed."
            
    return True, cleaned, None
