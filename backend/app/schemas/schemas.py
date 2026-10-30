from typing import List, Optional, Any, Dict
from pydantic import BaseModel, EmailStr, Field

# ----------------- Auth Schemas -----------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    email: str
    institution_id: Optional[str] = None
    student_internal_id: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class UserProfile(BaseModel):
    id: str
    email: str
    name: str
    role: str
    institution_id: Optional[str] = None
    student_internal_id: Optional[str] = None

# ----------------- Intake Schemas -----------------
class CourseIntakeBase(BaseModel):
    academic_year: str = "2024-2025"
    programme: str
    course: str
    approved_intake: int = Field(ge=1, description="AICTE Approved Core Intake")
    tfw_supernumerary_quota: int = Field(ge=0, default=0)
    nri_supernumerary_quota: int = Field(ge=0, default=0)
    fn_supernumerary_quota: int = Field(ge=0, default=0)
    status: str = "APPROVED"

class CourseIntakeOut(CourseIntakeBase):
    id: int
    institution_id: str
    actual_enrolment: Optional[int] = 0
    actual_supernumerary: Optional[int] = 0
    occupancy_rate: Optional[float] = 0.0
    is_over_admitted: Optional[bool] = False

    model_config = {"from_attributes": True}

# ----------------- Institution Schemas -----------------
class InstitutionBase(BaseModel):
    aicte_permanent_id: str
    name: str
    state: str
    district: str
    address: Optional[str] = None
    institution_type: str = "PRIVATE_UNAIDED"
    approval_session: str = "2024-2025"
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

class InstitutionOut(InstitutionBase):
    id: str
    total_approved_intake: Optional[int] = 0
    total_enrolled: Optional[int] = 0
    intake_status: Optional[str] = "COMPLIANT"
    intakes: Optional[List[CourseIntakeOut]] = []

    model_config = {"from_attributes": True}

# ----------------- Student Schemas -----------------
class StudentCreate(BaseModel):
    internal_id: str
    academic_year: str = "2024-2025"
    programme: str
    course: str
    admission_year: int = 2024
    apaar_id: str  # Plain 12-digit provided during entry; validated & hashed immediately
    student_name: str
    date_of_birth: str  # YYYY-MM-DD
    gender: str = "MALE"
    category: str = "GENERAL"
    is_supernumerary: bool = False
    supernumerary_type: str = "NONE"
    nri_status: bool = False
    oci_status: bool = False
    foreign_national_status: bool = False
    admission_status: str = "ENROLLED"

class StudentOut(BaseModel):
    id: str
    internal_id: str
    institution_id: str
    institution_name: str
    academic_year: str
    programme: str
    course: str
    admission_year: int
    apaar_masked: str  # ALWAYS MASKED FOR DATA PRIVACY (e.g. •••• •••• 1098)
    student_name: str
    date_of_birth: str
    gender: str
    category: str
    is_supernumerary: bool
    supernumerary_type: str
    nri_status: bool
    oci_status: bool
    foreign_national_status: bool
    admission_status: str
    record_status: str
    discrepancy_reason: Optional[str] = None
    verification_token: str
    credential_signature: str

    model_config = {"from_attributes": True}

class StudentCredentialDetail(StudentOut):
    qr_payload: str
    qr_code_base64: Optional[str] = None
    simulated_gateway_status: Optional[Dict[str, Any]] = None

# ----------------- Bulk Import & Staging -----------------
class ImportBatchResult(BaseModel):
    batch_id: str
    filename: str
    total_rows: int
    valid_rows: int
    error_rows: int
    status: str
    staged_errors: List[Dict[str, Any]] = []

class ResolveRowItem(BaseModel):
    row_index: int
    internal_id: str
    student_name: str
    apaar_id: str
    course: str
    date_of_birth: str
    category: str = "GENERAL"
    supernumerary_type: str = "NONE"

class ResolveBatchRequest(BaseModel):
    batch_id: str
    resolved_rows: List[ResolveRowItem]

# ----------------- Verification Schemas -----------------
class VerificationRequest(BaseModel):
    token: str
    verifier_name: str
    verifier_organization: str
    purpose: str

class VerificationResponse(BaseModel):
    status: str  # VERIFIED, INVALID, EXPIRED, NOT_FOUND
    is_valid: bool
    verification_code: str
    student_name: Optional[str] = None
    internal_id: Optional[str] = None
    apaar_masked: Optional[str] = None
    institution_name: Optional[str] = None
    programme: Optional[str] = None
    course: Optional[str] = None
    academic_year: Optional[str] = None
    admission_status: Optional[str] = None
    digital_signature: Optional[str] = None
    signature_verified: bool = False
    issued_on: Optional[str] = None
    gateway_note: str

# ----------------- Analytics & Discrepancies -----------------
class DuplicateApaarAlert(BaseModel):
    apaar_hash: str
    apaar_masked: str
    student_name: str
    institutions_involved: List[str]
    courses_involved: List[str]
    academic_year: str
    flag: str = "CONCURRENT_ENROLMENT_DISCREPANCY"

class NationalAnalytics(BaseModel):
    total_institutions: int
    total_programmes: int
    total_approved_intake: int
    total_actual_enrolled: int
    total_supernumerary_enrolled: int
    overall_occupancy_rate: float
    over_admission_violations: int
    duplicate_apaar_violations: int
    total_verifications_performed: int
    recent_audit_actions: List[Dict[str, Any]]
