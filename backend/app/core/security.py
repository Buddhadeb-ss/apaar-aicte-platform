import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from .config import settings

def hash_password(password: str) -> str:
    """Generate PBKDF2-HMAC-SHA256 password hash with 100,000 iterations."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"{salt.hex()}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against PBKDF2 hash."""
    try:
        salt_hex, key_hex = hashed_password.split('$')
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        check_key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(key, check_key)
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None

def generate_credential_signature(token: str, student_internal_id: str, apaar_hash: str, institution_id: str) -> str:
    """
    Generate an HMAC-SHA256 tamper-evident server signature for the student credential pass.
    Combines the random token, internal ID, institution ID, and APAAR hash with the master server key.
    """
    message = f"AICTE-VERIFIED:{token}:{student_internal_id}:{institution_id}:{apaar_hash}".encode('utf-8')
    sig = hmac.new(settings.SECRET_KEY.encode('utf-8'), message, hashlib.sha256).hexdigest()
    return f"SIG_v1_{sig[:32]}"

def verify_credential_signature(token: str, student_internal_id: str, apaar_hash: str, institution_id: str, signature: str) -> bool:
    """Verify that the provided signature matches the server-generated signature."""
    expected = generate_credential_signature(token, student_internal_id, apaar_hash, institution_id)
    return hmac.compare_digest(expected, signature)
