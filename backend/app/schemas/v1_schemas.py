from typing import List, Optional, Any, Dict, Generic, TypeVar
from pydantic import BaseModel, Field, EmailStr

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    total_pages: int

# ----------------- AUTH & PERSONAS -----------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    email: str
    institution_id: Optional[str] = None
    student_id: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str
    institution_id: Optional[str] = None
    student_id: Optional[str] = None

    model_config = {"from_attributes": True}

class DemoProfileOut(BaseModel):
    role: str
    email: str
    label: str
    name: str
    institution_id: Optional[str] = None
    student_id: Optional[str] = None
    description: str
    icon: str

# ----------------- PROGRAMMES & COURSES -----------------
class ProgrammeOut(BaseModel):
    id: str
    code: str
    name: str
    level: str
    duration_years: int

    model_config = {"from_attributes": True}

class CourseOut(BaseModel):
    id: str
    programme_id: str
    code: str
    name: str
    degree: str

    model_config = {"from_attributes": True}

# ----------------- INSTITUTIONS & INTAKES -----------------
class CourseIntakeDetail(BaseModel):
    id: int
    institution_id: str
    course_id: str
    course_name: str
    programme_name: str
    academic_year: str
    approved_intake: int
    tfw_supernumerary_quota: int
    nri_supernumerary_quota: int
    fn_supernumerary_quota: int
    actual_enrolment: int = 0
    actual_supernumerary: int = 0
    occupancy_rate: float = 0.0
    is_over_admitted: bool = False

class InstitutionOut(BaseModel):
    id: str
    aicte_permanent_id: str
    name: str
    state: str
    district: str
    address: Optional[str] = None
    institution_type: str
    approval_session: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    total_approved_intake: int = 0
    total_enrolled: int = 0
    intake_status: str = "COMPLIANT"
    intakes: List[CourseIntakeDetail] = []

    model_config = {"from_attributes": True}

class CourseReconciliationRow(BaseModel):
    course_id: str
    course: str
    programme: str
    approved_intake: int
    regular_enrolled: int
    variance: int
    is_over_admitted: bool
    tfw_quota: int
    tfw_enrolled: int
    nri_quota: int
    nri_enrolled: int
    fn_quota: int
    fn_enrolled: int
    total_students: int
    compliance_status: str

class IntakeReconciliationReport(BaseModel):
    institution_id: str
    institution_name: str
    aicte_id: str
    academic_year: str
    reconciliation_rows: List[CourseReconciliationRow]

# ----------------- STUDENTS & ENROLMENTS -----------------
class StudentCreateIn(BaseModel):
    student_name: str
    date_of_birth: str  # YYYY-MM-DD
    gender: str = "MALE"
    category: str = "GENERAL"
    internal_student_id: str  # Roll No
    course_id: str
    academic_year: str = "2024-2025"
    admission_year: int = 2024
    apaar_id: str  # Plain 12-digit; validated & salted immediately
    is_supernumerary: bool = False
    supernumerary_type: str = "NONE"
    nri_status: bool = False
    oci_status: bool = False
    foreign_national_status: bool = False

class StudentEnrolmentOut(BaseModel):
    id: str
    student_id: str
    internal_student_id: str
    institution_id: str
    institution_name: str
    course_id: str
    course_name: str
    programme_name: str
    academic_year: str
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

class StudentCredentialPass(StudentEnrolmentOut):
    qr_payload: str
    qr_code_base64: str
    simulated_gateway_status: Optional[Dict[str, Any]] = None
    consent_status: str = "GRANTED"

class StudentUpdateIn(BaseModel):
    student_name: str
    date_of_birth: str
    gender: str = "MALE"
    category: str = "GENERAL"
    internal_student_id: str
    course_id: str
    academic_year: str = "2024-2025"
    admission_year: int = 2024
    admission_status: str = "ENROLLED"
    apaar_id: Optional[str] = None  # If provided, re-validated with Verhoeff
    is_supernumerary: bool = False
    supernumerary_type: str = "NONE"
    nri_status: bool = False
    oci_status: bool = False
    foreign_national_status: bool = False

class StudentHistoryItem(BaseModel):
    id: int
    event_type: str
    actor_email: str
    actor_role: str
    timestamp: str
    details: Optional[str] = None

class BulkDryRunRowError(BaseModel):
    row_index: int
    field_name: str
    error_code: str
    error_message: str
    severity: str = "CRITICAL"

class BulkDryRunResult(BaseModel):
    total_rows: int
    valid_rows_count: int
    invalid_rows_count: int
    duplicate_rows_count: int
    preview_rows: List[Dict[str, Any]]
    errors: List[BulkDryRunRowError]
    can_commit: bool

class BulkCommitIn(BaseModel):
    filename: str
    academic_year: str = "2024-2025"
    institution_id: Optional[str] = None
    rows: List[Dict[str, Any]]

class BulkCommitSummary(BaseModel):
    job_id: str
    filename: str
    academic_year: str
    total_records: int
    accepted_count: int
    rejected_count: int
    duplicate_count: int
    status: str
    message: str

# ----------------- BULK UPLOADS & VALIDATION -----------------
class BulkUploadJobOut(BaseModel):
    id: str
    institution_id: str
    filename: str
    academic_year: str
    total_records: int
    valid_records: int
    error_records: int
    status: str
    created_at: str

    model_config = {"from_attributes": True}

class ValidationIssueOut(BaseModel):
    id: int
    job_id: Optional[str] = None
    institution_id: Optional[str] = None
    student_id: Optional[str] = None
    enrolment_id: Optional[str] = None
    row_number: Optional[int] = None
    rule_id: str = "RULE_UNKNOWN"
    field_name: str
    error_code: str
    error_message: str
    suggested_remediation: Optional[str] = None
    severity: str
    anomaly_score: float = 0.0
    raw_data: Optional[Dict[str, Any]] = None
    resolution_status: str
    reviewed_by_user_id: Optional[str] = None
    reviewed_by_email: Optional[str] = None
    reviewed_at: Optional[str] = None
    resolution_reason: Optional[str] = None
    created_at: Optional[str] = None

class ValidationWorkbenchIssueOut(BaseModel):
    id: int
    job_id: Optional[str] = None
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None
    student_id: Optional[str] = None
    enrolment_id: Optional[str] = None
    row_number: Optional[int] = None
    rule_id: str
    field_name: str
    error_code: str
    error_message: str
    suggested_remediation: Optional[str] = None
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    anomaly_score: float = 0.0
    is_potential_anomaly: bool = False
    resolution_status: str  # NEW, UNDER_REVIEW, RESOLVED, DISMISSED
    raw_data: Optional[Dict[str, Any]] = None
    reviewed_by_user_id: Optional[str] = None
    reviewed_by_email: Optional[str] = None
    reviewed_at: Optional[str] = None
    resolution_reason: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    student_name: Optional[str] = None
    internal_student_id: Optional[str] = None
    apaar_masked: Optional[str] = None

class ValidationWorkbenchSummary(BaseModel):
    total_issues: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    new_count: int
    under_review_count: int
    resolved_count: int
    dismissed_count: int
    anomaly_score: float
    risk_level: str
    is_potential_anomaly: bool
    rule_breakdown: Dict[str, int]

class ValidationWorkbenchResponse(BaseModel):
    items: List[ValidationWorkbenchIssueOut]
    summary: ValidationWorkbenchSummary
    total: int
    page: int
    limit: int
    total_pages: int

class IssueStatusUpdateIn(BaseModel):
    resolution_status: str = Field(..., description="NEW, UNDER_REVIEW, RESOLVED, or DISMISSED")
    resolution_reason: str = Field(..., min_length=3, description="Mandatory audit trail reason for status change")
    remediation_action: Optional[str] = None

class BulkIssueReviewIn(BaseModel):
    issue_ids: List[int] = Field(..., min_length=1)
    resolution_status: str = Field(..., description="UNDER_REVIEW, RESOLVED, or DISMISSED")
    resolution_reason: str = Field(..., min_length=3, description="Reason applied to all selected issues")

class ValidationAuditResponse(BaseModel):
    status: str
    institution_id: str
    academic_year: str
    total_issues_found: int
    new_issues_persisted: int
    anomaly_score: float
    risk_level: str
    is_potential_anomaly: bool
    explanation: str

class ResolveIssueItem(BaseModel):
    issue_id: int
    internal_student_id: str
    student_name: str
    apaar_id: str
    course_id: str
    date_of_birth: str
    category: str = "GENERAL"
    supernumerary_type: str = "NONE"

class BatchResolveIn(BaseModel):
    job_id: str
    resolved_rows: List[ResolveIssueItem]

# ----------------- VERIFICATION REQUESTS -----------------
class VerificationRequestIn(BaseModel):
    token: str
    verifier_name: str
    verifier_organization: str
    purpose: str

class VerificationResponseOut(BaseModel):
    status: str  # VERIFIED, INVALID_SIGNATURE, NOT_FOUND, REVOKED
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
    consent_verified: bool = True
    gateway_note: str

# ----------------- DASHBOARD & DUPLICATES -----------------
class DuplicateCollisionAlert(BaseModel):
    apaar_hash: str
    apaar_masked: str
    student_name: str
    student_id: str
    enrolments: List[Dict[str, Any]]
    flag: str = "CONCURRENT_ENROLMENT_DISCREPANCY"

class NationalDashboardMetrics(BaseModel):
    total_institutions: int
    total_programmes: int
    total_courses: int
    total_approved_intake: int
    total_actual_enrolled: int
    total_supernumerary_enrolled: int
    overall_occupancy_rate: float
    over_admission_violations: int
    duplicate_apaar_violations: int
    total_verifications_performed: int
    recent_audit_events: List[Dict[str, Any]]
    total_validation_issues: int = 0
    critical_validation_issues: int = 0
    unresolved_validation_issues: int = 0

# ----------------- AUDIT EVENTS -----------------
class AuditEventOut(BaseModel):
    id: int
    institution_id: Optional[str] = None
    actor_email: str
    actor_role: str
    event_type: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: str
    timestamp: str

    model_config = {"from_attributes": True}


# ----------------- AICTE COMMAND CENTER & ANALYTICS SCHEMAS -----------------

class SeverityCounts(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    total: int = 0

class RecentUploadJobSummary(BaseModel):
    id: str
    filename: str
    institution_id: str
    institution_name: str
    academic_year: str
    status: str
    total_records: int
    valid_records: int
    error_records: int
    created_at: str

class RecentVerificationSummary(BaseModel):
    id: str
    token: str
    verifier_name: str
    verifier_organization: str
    purpose: str
    verification_result: str
    student_name: Optional[str] = None
    apaar_masked: Optional[str] = None
    institution_name: Optional[str] = None
    created_at: str

class ExcessInstitutionSummary(BaseModel):
    institution_id: str
    institution_name: str
    aicte_id: str
    state: str
    approved_intake: int
    enrolled_count: int
    excess_count: int

class AicteCommandCenterSummary(BaseModel):
    total_registered_institutions: int
    total_student_identities: int  # Distinct unique physical students
    total_active_enrolments: int   # Active enrolment seats occupied
    total_approved_intake: int
    intake_utilization_pct: float
    total_supernumerary_admissions: int
    pending_validation_issues: SeverityCounts
    duplicate_alerts_count: int
    institutions_with_excess_enrolment: int
    excess_institutions: List[ExcessInstitutionSummary] = []
    recent_uploads: List[RecentUploadJobSummary] = []
    failed_import_jobs_count: int = 0
    recent_verification_requests: List[RecentVerificationSummary] = []
    data_completeness_pct: float
    is_synthetic_data: bool = True

class StateEnrolmentStat(BaseModel):
    state: str
    approved_intake: int
    actual_enrolment: int
    supernumerary_enrolment: int
    institutions_count: int
    utilization_rate: float

class ProgrammeEnrolmentStat(BaseModel):
    programme_id: str
    programme_name: str
    programme_code: str
    approved_intake: int
    actual_enrolment: int
    supernumerary_enrolment: int
    utilization_rate: float

class AcademicYearTrendStat(BaseModel):
    academic_year: str
    approved_intake: int
    actual_enrolment: int
    supernumerary: int
    utilization_rate: float

class InstitutionIntakeVsEnrolmentStat(BaseModel):
    institution_id: str
    institution_name: str
    aicte_id: str
    state: str
    approved_intake: int
    actual_enrolment: int
    supernumerary: int
    utilization_rate: float
    is_over_admitted: bool

class CategoryBreakdownStat(BaseModel):
    category: str
    count: int
    percentage: float

class QuotaBreakdownStat(BaseModel):
    quota: str
    count: int
    percentage: float

class ValidationIssueTrendStat(BaseModel):
    rule_id: str
    rule_name: str
    severity: str
    total_count: int
    unresolved_count: int

class InstitutionDataCompletenessStat(BaseModel):
    institution_id: str
    institution_name: str
    aicte_id: str
    total_students: int
    completeness_pct: float

class TopInstitutionReviewStat(BaseModel):
    institution_id: str
    institution_name: str
    aicte_id: str
    state: str
    risk_score: float
    risk_level: str
    flags: List[str]
    over_admitted_count: int
    critical_issues_count: int
    collision_count: int
    completeness_pct: float

class AicteAnalyticsResponse(BaseModel):
    academic_year_filter: Optional[str] = None
    programme_filter: Optional[str] = None
    state_filter: Optional[str] = None
    enrolment_by_state: List[StateEnrolmentStat]
    programme_wise_enrolment: List[ProgrammeEnrolmentStat]
    academic_year_trends: List[AcademicYearTrendStat]
    institution_intake_vs_enrolment: List[InstitutionIntakeVsEnrolmentStat]
    category_breakdown: List[CategoryBreakdownStat]
    quota_breakdown: List[QuotaBreakdownStat]
    validation_issue_trends: List[ValidationIssueTrendStat]
    data_completeness_by_institution: List[InstitutionDataCompletenessStat]
    top_institutions_requiring_review: List[TopInstitutionReviewStat]
    is_synthetic_data: bool = True

# ----------------- INSTITUTION DASHBOARD SUMMARY -----------------

class CourseIntakeOccupancyStat(BaseModel):
    course_id: str
    course_name: str
    degree: str
    programme_name: str
    approved_intake: int
    regular_enrolled: int
    supernumerary_enrolled: int
    utilization_pct: float
    is_over_admitted: bool

class InstitutionDashboardSummary(BaseModel):
    institution_id: str
    institution_name: str
    aicte_permanent_id: str
    state: str
    district: str
    approval_session: str
    institution_type: str
    contact_email: Optional[str] = None
    total_approved_intake: int
    total_actual_enrolled: int
    total_supernumerary_enrolled: int
    intake_utilization_pct: float
    intake_compliance_status: str
    programme_breakdown: List[CourseIntakeOccupancyStat]
    recent_uploads: List[RecentUploadJobSummary]
    failed_import_jobs_count: int
    unresolved_issues_count: int
    unresolved_issues_by_severity: SeverityCounts
    student_record_completeness_pct: float
    missing_fields_breakdown: Dict[str, int]
    recent_verifications: List[RecentVerificationSummary]
    is_synthetic_data: bool = True
