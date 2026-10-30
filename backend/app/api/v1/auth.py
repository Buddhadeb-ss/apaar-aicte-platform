from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..deps import get_db, get_current_user
from ...database.models import User
from ...schemas.v1_schemas import Token, LoginRequest, UserOut, DemoProfileOut
from ...core.security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication & User Management"])

DEMO_PROFILES: List[dict] = [
    {
        "role": "AICTE_ADMIN",
        "email": "admin@aicte.gov.in",
        "label": "AICTE Administrator",
        "name": "Dr. K. S. Sundaram",
        "institution_id": None,
        "student_id": None,
        "description": "National scrutiny, sanctioned intake enforcement, and multi-college APAAR collision resolution.",
        "icon": "ShieldCheck"
    },
    {
        "role": "INSTITUTION_ADMIN",
        "email": "registrar@apex.edu",
        "label": "Institution Administrator (Apex Tech)",
        "name": "Prof. Sunita Deshmukh",
        "institution_id": "inst-apex-1001",
        "student_id": None,
        "description": "Institutional governance, course intake limits, confirmed student rosters, and audit reports.",
        "icon": "Building2"
    },
    {
        "role": "INSTITUTION_OPERATOR",
        "email": "operator@apex.edu",
        "label": "Institution Operator (Apex Tech)",
        "name": "Ramesh Joshi",
        "institution_id": "inst-apex-1001",
        "student_id": None,
        "description": "Data entry operations, CSV bulk onboarding, and inline staging error resolution.",
        "icon": "FileSpreadsheet"
    },
    {
        "role": "STUDENT_VIEWER",
        "email": "student@apex.edu",
        "label": "Student Viewer (Aarav Sharma)",
        "name": "Aarav Sharma (AIT-2024-CSE-007)",
        "institution_id": "inst-apex-1001",
        "student_id": "stud-uuid-aarav-sharma-2024",
        "description": "Privacy-preserving student credential pass, masked APAAR ID, and verifiable QR code pass.",
        "icon": "GraduationCap"
    },
    {
        "role": "AUTHORIZED_VERIFIER",
        "email": "verifier@tcs.com",
        "label": "Authorized Verifier (TCS HR)",
        "name": "Priya Varma (Lead HR, TCS)",
        "institution_id": None,
        "student_id": None,
        "description": "Third-party background verification, cryptographic QR signature verification, and audit logs.",
        "icon": "QrCode"
    },
    {
        "role": "INSTITUTION_ADMIN",
        "email": "principal@beacon.ac.in",
        "label": "Institution Administrator (Beacon College)",
        "name": "Dr. Raghavan Nair (Dean, Beacon College)",
        "institution_id": "inst-beacon-2002",
        "student_id": None,
        "description": "Institutional governance for Beacon College of Engineering (Karnataka).",
        "icon": "Building2"
    }
]

@router.get("/demo-profiles", response_model=List[DemoProfileOut])
def get_demo_profiles():
    """List 5 pre-configured demonstration evaluation accounts."""
    return DEMO_PROFILES

@router.post("/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with institutional email and password."""
    user = db.query(User).filter(User.email == credentials.email.strip().lower()).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password credentials."
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or suspended."
        )

    token_data = {
        "sub": user.email,
        "role": user.role,
        "name": user.name,
        "institution_id": user.institution_id,
        "student_id": user.student_id
    }
    access_token = create_access_token(token_data)
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        name=user.name,
        email=user.email,
        institution_id=user.institution_id,
        student_id=user.student_id
    )

@router.post("/demo-login/{persona_index}", response_model=Token)
def quick_demo_login(persona_index: int, db: Session = Depends(get_db)):
    """Instant 1-click evaluation login using index (0 to 4)."""
    if persona_index < 0 or persona_index >= len(DEMO_PROFILES):
        raise HTTPException(status_code=400, detail="Invalid demo profile index.")
    
    target_email = DEMO_PROFILES[persona_index]["email"]
    user = db.query(User).filter(User.email == target_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Demo user profile not found.")

    token_data = {
        "sub": user.email,
        "role": user.role,
        "name": user.name,
        "institution_id": user.institution_id,
        "student_id": user.student_id
    }
    access_token = create_access_token(token_data)
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        name=user.name,
        email=user.email,
        institution_id=user.institution_id,
        student_id=user.student_id
    )

@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Retrieve profile and institutional scope for authenticated session."""
    return current_user
