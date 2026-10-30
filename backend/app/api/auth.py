from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .deps import get_db, get_current_user
from ..database.models import User, Institution, Student
from ..schemas.schemas import Token, LoginRequest, UserProfile
from ..core.security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication & Personas"])

DEMO_PROFILES = [
    {
        "role": "AICTE_ADMIN",
        "email": "admin@aicte.gov.in",
        "label": "AICTE National Scrutiny Director",
        "name": "Dr. K. S. Sundaram",
        "description": "National overview, intake compliance, quota limits, cross-institution duplicate APAAR detection.",
        "icon": "ShieldCheck"
    },
    {
        "role": "INSTITUTE_ADMIN",
        "email": "registrar@apex.edu",
        "label": "Apex Institute Registrar",
        "name": "Prof. Sunita Deshmukh",
        "institution_id": "inst-apex-1001",
        "description": "Approved intake monitoring, student onboarding, CSV batch upload, error resolution queue.",
        "icon": "Building2"
    },
    {
        "role": "INSTITUTE_ADMIN",
        "email": "principal@beacon.ac.in",
        "label": "Beacon College Dean",
        "name": "Dr. Raghavan Nair",
        "institution_id": "inst-beacon-2002",
        "description": "Government-aided institute with IT & Mechanical courses, reconciliation review.",
        "icon": "GraduationCap"
    },
    {
        "role": "STUDENT",
        "email": "student@apex.edu",
        "label": "Enrolled Student (Aarav Sharma)",
        "name": "Aarav Sharma (AIT-2024-CSE-007)",
        "institution_id": "inst-apex-1001",
        "description": "Student record portal, privacy-masked APAAR view, signed digital verifiable credential pass.",
        "icon": "User"
    },
    {
        "role": "VERIFIER",
        "email": "verifier@tcs.com",
        "label": "Third-Party Verifier (TCS HR)",
        "name": "Priya Varma (Lead HR, TCS)",
        "description": "QR code scanner, cryptographic signature verification, background check audit.",
        "icon": "QrCode"
    }
]

@router.get("/demo-profiles", response_model=List[Dict[str, Any]])
def get_demo_profiles():
    """Return list of quick 1-click evaluation login personas."""
    return DEMO_PROFILES

@router.post("/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Standard credential-based authentication."""
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended."
        )

    token_data = {
        "sub": user.email,
        "role": user.role,
        "name": user.name,
        "institution_id": user.institution_id,
        "student_internal_id": user.student_internal_id
    }
    access_token = create_access_token(token_data)
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        name=user.name,
        email=user.email,
        institution_id=user.institution_id,
        student_internal_id=user.student_internal_id
    )

@router.post("/demo-login/{persona_index}", response_model=Token)
def quick_demo_login(persona_index: int, db: Session = Depends(get_db)):
    """One-click evaluation login using index from demo profiles."""
    if persona_index < 0 or persona_index >= len(DEMO_PROFILES):
        raise HTTPException(status_code=400, detail="Invalid demo profile index.")
    
    target_email = DEMO_PROFILES[persona_index]["email"]
    user = db.query(User).filter(User.email == target_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Demo user record not found.")

    token_data = {
        "sub": user.email,
        "role": user.role,
        "name": user.name,
        "institution_id": user.institution_id,
        "student_internal_id": user.student_internal_id
    }
    access_token = create_access_token(token_data)
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        name=user.name,
        email=user.email,
        institution_id=user.institution_id,
        student_internal_id=user.student_internal_id
    )

@router.get("/me", response_model=UserProfile)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Return profile details for the authenticated user."""
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        institution_id=current_user.institution_id,
        student_internal_id=current_user.student_internal_id
    )
