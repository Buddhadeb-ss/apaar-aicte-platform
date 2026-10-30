import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text,
    UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from .session import Base
from ..core.identifiers import generate_uuid

# ----------------- 1. INSTITUTIONS & USERS -----------------

class Institution(Base):
    __tablename__ = "institutions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    aicte_permanent_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    state = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False)
    address = Column(Text, nullable=True)
    institution_type = Column(String(100), default="PRIVATE_UNAIDED")  # GOVERNMENT, GOVERNMENT_AIDED, PRIVATE_UNAIDED, DEEMED_UNIVERSITY
    approval_session = Column(String(50), default="2024-2025")
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    users = relationship("User", back_populates="institution")
    intakes = relationship("InstitutionIntake", back_populates="institution", cascade="all, delete-orphan")
    enrolments = relationship("StudentEnrolment", back_populates="institution")
    upload_jobs = relationship("BulkUploadJob", back_populates="institution")

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # AICTE_ADMIN, INSTITUTION_ADMIN, INSTITUTION_OPERATOR, STUDENT_VIEWER, AUTHORIZED_VERIFIER
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    institution = relationship("Institution", back_populates="users")
    student = relationship("Student", back_populates="user", uselist=False)

    @property
    def student_internal_id(self):
        if self.student and self.student.enrolments:
            return self.student.enrolments[0].internal_student_id
        return None

# ----------------- 2. PROGRAMMES & COURSES -----------------

class Programme(Base):
    __tablename__ = "programmes"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, nullable=False, index=True)  # e.g. ENG_TECH, MGMT, PHARM, MCA
    name = Column(String(255), nullable=False)  # e.g. Engineering & Technology
    level = Column(String(50), default="UNDERGRADUATE")  # UNDERGRADUATE, POSTGRADUATE, DIPLOMA
    duration_years = Column(Integer, default=4)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    courses = relationship("Course", back_populates="programme")
    intakes = relationship("InstitutionIntake", back_populates="programme")

    def __str__(self):
        return self.name

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    programme_id = Column(String(36), ForeignKey("programmes.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # e.g. CSE, AI_DS, ECE, MBA
    name = Column(String(255), nullable=False)  # e.g. Computer Science & Engineering
    degree = Column(String(50), default="B.Tech")  # B.Tech, M.Tech, MBA, MCA, B.Pharm
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    programme = relationship("Programme", back_populates="courses")
    intakes = relationship("InstitutionIntake", back_populates="course")
    enrolments = relationship("StudentEnrolment", back_populates="course")

    def __str__(self):
        return self.name

# ----------------- 3. INTAKE LIMITS & RECONCILIATION -----------------

class InstitutionIntake(Base):
    """
    CRITICAL STATUTORY SEPARATION:
    Sanctioned intake is defined strictly at the institution & course level.
    It is NEVER stored as a student-level property.
    """
    __tablename__ = "institution_intakes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    programme_id = Column(String(36), ForeignKey("programmes.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    academic_year = Column(String(50), nullable=False)  # e.g. "2024-2025"
    
    approved_intake = Column(Integer, nullable=False, default=60)  # Core regular approved intake
    tfw_supernumerary_quota = Column(Integer, nullable=False, default=3)  # Tuition Fee Waiver (5% max)
    nri_supernumerary_quota = Column(Integer, nullable=False, default=3)  # NRI Quota (5% max)
    fn_supernumerary_quota = Column(Integer, nullable=False, default=9)   # Foreign National / PIO (15% max)
    status = Column(String(50), default="APPROVED")  # APPROVED, UNDER_SCRUTINY, SUSPENDED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    institution = relationship("Institution", back_populates="intakes")
    programme = relationship("Programme", back_populates="intakes")
    course = relationship("Course", back_populates="intakes")

    __table_args__ = (
        UniqueConstraint('institution_id', 'course_id', 'academic_year', name='uq_inst_course_academic_year'),
    )

# ----------------- 4. STUDENTS & MULTIPLE ENROLMENTS -----------------

class Student(Base):
    """
    Core Student Identity:
    Every student has a stable RFC 4122 internal UUID.
    Multiple academic enrolments are modeled separately in `student_enrolments`.
    """
    __tablename__ = "students"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    student_name = Column(String(255), nullable=False)
    date_of_birth = Column(String(20), nullable=False)  # YYYY-MM-DD
    gender = Column(String(20), default="MALE")  # MALE, FEMALE, OTHER
    category = Column(String(50), default="GENERAL")  # GENERAL, OBC, SC, ST, EWS
    
    # APAAR ID Privacy & Collision Indexing:
    apaar_id_encrypted = Column(String(255), nullable=False)
    apaar_hash = Column(String(64), nullable=False, index=True)  # SHA-256 for collision checks
    apaar_masked = Column(String(20), nullable=False)  # •••• •••• XXXX
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="student")
    enrolments = relationship("StudentEnrolment", back_populates="student", cascade="all, delete-orphan")
    credentials = relationship("SignedCredential", back_populates="student", cascade="all, delete-orphan")
    consents = relationship("ConsentRecord", back_populates="student", cascade="all, delete-orphan")

    @property
    def internal_id(self):
        return self.enrolments[0].internal_student_id if self.enrolments else ""

    @property
    def institution_id(self):
        return self.enrolments[0].institution_id if self.enrolments else ""

    @property
    def institution_name(self):
        if self.enrolments and self.enrolments[0].institution and self.enrolments[0].institution.name:
            return self.enrolments[0].institution.name
        return ""

    @property
    def academic_year(self):
        return self.enrolments[0].academic_year if self.enrolments else "2024-2025"

    @property
    def admission_year(self):
        return self.enrolments[0].admission_year if self.enrolments else 2024

    @property
    def programme(self):
        if self.enrolments and self.enrolments[0].course and self.enrolments[0].course.programme:
            return self.enrolments[0].course.programme.name
        return "Engineering & Technology"

    @property
    def course(self):
        if self.enrolments and self.enrolments[0].course:
            return self.enrolments[0].course.name
        return ""

    @property
    def is_supernumerary(self):
        return self.enrolments[0].is_supernumerary if self.enrolments else False

    @property
    def supernumerary_type(self):
        return self.enrolments[0].supernumerary_type if self.enrolments else "NONE"

    @property
    def nri_status(self):
        return self.enrolments[0].nri_status if self.enrolments else False

    @property
    def oci_status(self):
        return self.enrolments[0].oci_status if self.enrolments else False

    @property
    def foreign_national_status(self):
        return self.enrolments[0].foreign_national_status if self.enrolments else False

    @property
    def admission_status(self):
        return self.enrolments[0].admission_status if self.enrolments else "ENROLLED"

    @property
    def record_status(self):
        return self.enrolments[0].record_status if self.enrolments else "ACCEPTED"

    @property
    def discrepancy_reason(self):
        return self.enrolments[0].discrepancy_reason if self.enrolments else None

    @property
    def verification_token(self):
        if self.credentials:
            return self.credentials[0].verification_token
        return self.id

    @property
    def credential_signature(self):
        if self.credentials:
            return self.credentials[0].signature_value
        return ""

class StudentEnrolment(Base):
    """
    Model multiple academic enrolments separately from student identity.
    Enforces uniqueness constraints per institution, session, and roll number.
    """
    __tablename__ = "student_enrolments"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    internal_student_id = Column(String(100), nullable=False)  # Normalized institutional Roll No
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year = Column(String(50), nullable=False)  # e.g. "2024-2025"
    admission_year = Column(Integer, nullable=False, default=2024)
    admission_category = Column(String(50), default="REGULAR")  # REGULAR, LATERAL_ENTRY
    
    # Quotas & Supernumerary Status:
    is_supernumerary = Column(Boolean, default=False)
    supernumerary_type = Column(String(50), default="NONE")  # NONE, TFW, EWS, J_AND_K_PMSSS, PM_CARES, SPORTS, NRI, OCI, FOREIGN_NATIONAL
    nri_status = Column(Boolean, default=False)
    oci_status = Column(Boolean, default=False)
    foreign_national_status = Column(Boolean, default=False)
    
    # Statuses:
    admission_status = Column(String(50), default="ENROLLED")  # ENROLLED, ADMITTED, PROVISIONAL, WITHDRAWN, COMPLETED
    record_status = Column(String(50), default="ACCEPTED")  # ACCEPTED, FLAGGED_DISCREPANCY, PENDING_REVIEW, REJECTED
    discrepancy_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    student = relationship("Student", back_populates="enrolments")
    institution = relationship("Institution", back_populates="enrolments")
    course = relationship("Course", back_populates="enrolments")
    credentials = relationship("SignedCredential", back_populates="enrolment")

    __table_args__ = (
        UniqueConstraint('institution_id', 'academic_year', 'internal_student_id', name='uq_inst_year_internal_roll'),
        Index('idx_enrolment_lookup', 'institution_id', 'academic_year', 'course_id'),
    )

# ----------------- 5. BULK UPLOADS & VALIDATION ISSUES -----------------

class BulkUploadJob(Base):
    __tablename__ = "bulk_upload_jobs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    filename = Column(String(255), nullable=False)
    academic_year = Column(String(50), nullable=False)
    total_records = Column(Integer, default=0)
    valid_records = Column(Integer, default=0)
    error_records = Column(Integer, default=0)
    status = Column(String(50), default="PENDING")  # PENDING, PROCESSING, COMPLETED, REQUIRES_RESOLUTION, FAILED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    institution = relationship("Institution", back_populates="upload_jobs")
    issues = relationship("ValidationIssue", back_populates="job", cascade="all, delete-orphan")

class ValidationIssue(Base):
    __tablename__ = "validation_issues"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    enrolment_id = Column(String(36), ForeignKey("student_enrolments.id", ondelete="SET NULL"), nullable=True, index=True)
    job_id = Column(String(36), ForeignKey("bulk_upload_jobs.id", ondelete="CASCADE"), nullable=True, index=True)
    
    row_number = Column(Integer, nullable=True)
    rule_id = Column(String(100), nullable=False, default="RULE_UNKNOWN", index=True)
    field_name = Column(String(100), nullable=False)
    error_code = Column(String(100), nullable=False, index=True)
    error_message = Column(Text, nullable=False)
    suggested_remediation = Column(Text, nullable=True)
    severity = Column(String(20), default="CRITICAL", index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    anomaly_score = Column(Float, default=0.0)
    raw_data_json = Column(Text, nullable=True)
    
    # Lifecycle Management: NEW, UNDER_REVIEW, RESOLVED, DISMISSED
    resolution_status = Column(String(50), default="NEW", index=True)
    reviewed_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_email = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    resolution_reason = Column(Text, nullable=True)
    resolved_data_json = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    job = relationship("BulkUploadJob", back_populates="issues")
    institution = relationship("Institution", foreign_keys=[institution_id])
    student = relationship("Student", foreign_keys=[student_id])
    enrolment = relationship("StudentEnrolment", foreign_keys=[enrolment_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])

# ----------------- 6. SIGNED CREDENTIALS & VERIFICATIONS -----------------

class SignedCredential(Base):
    __tablename__ = "signed_credentials"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    enrolment_id = Column(String(36), ForeignKey("student_enrolments.id", ondelete="CASCADE"), nullable=False, index=True)
    verification_token = Column(String(64), unique=True, nullable=False, index=True, default=generate_uuid)
    signature_algorithm = Column(String(50), default="HMAC-SHA256")
    signature_value = Column(String(255), nullable=False)
    issued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)
    is_revoked = Column(Boolean, default=False)

    student = relationship("Student", back_populates="credentials")
    enrolment = relationship("StudentEnrolment", back_populates="credentials")

class VerificationRequest(Base):
    __tablename__ = "verification_requests"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    token = Column(String(64), nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    enrolment_id = Column(String(36), ForeignKey("student_enrolments.id", ondelete="SET NULL"), nullable=True)
    verifier_name = Column(String(255), nullable=False)
    verifier_organization = Column(String(255), nullable=False)
    purpose = Column(String(255), nullable=False)
    verification_result = Column(String(50), nullable=False)  # VERIFIED, INVALID_SIGNATURE, NOT_FOUND, REVOKED
    consent_verified = Column(Boolean, default=True)
    ip_address = Column(String(100), default="127.0.0.1")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    student = relationship("Student")
    enrolment = relationship("StudentEnrolment")

    def __init__(self, *args, **kwargs):
        if "status" in kwargs and "verification_result" not in kwargs:
            kwargs["verification_result"] = kwargs.pop("status")
        super().__init__(*args, **kwargs)

    @property
    def status(self):
        return self.verification_result

    @status.setter
    def status(self, val):
        self.verification_result = val

    @property
    def timestamp(self):
        return self.created_at

# ----------------- 7. AUDIT EVENTS & CONSENT RECORDS -----------------

class AuditEvent(Base):
    __tablename__ = "audit_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(String(36), nullable=True, index=True)
    actor_user_id = Column(String(36), nullable=True)
    actor_email = Column(String(255), nullable=False)
    actor_role = Column(String(50), nullable=False)
    event_type = Column(String(100), nullable=False)  # e.g. AUTH_LOGIN, STUDENT_ENROLLED, INTAKE_MODIFIED, CREDENTIAL_VERIFIED
    resource_type = Column(String(100), nullable=False, default="SYSTEM")
    resource_id = Column(String(255), nullable=True)
    details_json = Column(Text, nullable=True)  # Strictly sanitized: NO raw APAAR or sensitive PII
    ip_address = Column(String(100), default="127.0.0.1")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __init__(self, *args, **kwargs):
        if "user_email" in kwargs and "actor_email" not in kwargs:
            kwargs["actor_email"] = kwargs.pop("user_email")
        if "role" in kwargs and "actor_role" not in kwargs:
            kwargs["actor_role"] = kwargs.pop("role")
        if "action" in kwargs and "event_type" not in kwargs:
            kwargs["event_type"] = kwargs.pop("action")
        if "details" in kwargs and "details_json" not in kwargs:
            kwargs["details_json"] = kwargs.pop("details")
        if "resource_type" not in kwargs:
            kwargs["resource_type"] = "SYSTEM"
        super().__init__(*args, **kwargs)

    @property
    def user_email(self):
        return self.actor_email

    @user_email.setter
    def user_email(self, val):
        self.actor_email = val

    @property
    def role(self):
        return self.actor_role

    @role.setter
    def role(self, val):
        self.actor_role = val

    @property
    def action(self):
        return self.event_type

    @action.setter
    def action(self, val):
        self.event_type = val

    @property
    def details(self):
        return self.details_json or self.resource_type

    @details.setter
    def details(self, val):
        self.details_json = val

class ConsentRecord(Base):
    """Simulated student consent record for third-party academic verification."""
    __tablename__ = "consent_records"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = Column(String(255), nullable=False)
    status = Column(String(50), default="GRANTED")  # GRANTED, REVOKED, PENDING
    granted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    valid_until = Column(DateTime, nullable=True)
    ip_address = Column(String(100), default="127.0.0.1")

    student = relationship("Student", back_populates="consents")

# ----------------- Compatibility Aliases -----------------
InstitutionCourseIntake = InstitutionIntake
AuditLog = AuditEvent
VerificationLog = VerificationRequest
ImportBatch = BulkUploadJob

