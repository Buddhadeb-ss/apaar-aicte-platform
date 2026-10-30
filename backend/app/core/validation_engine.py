import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Set
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from .identifiers import (
    validate_apaar_format,
    normalize_identifier,
    clean_apaar_id,
    hash_apaar_id,
    mask_apaar_id
)
from ..database.models import (
    Institution, Course, Programme, InstitutionIntake,
    Student, StudentEnrolment, ValidationIssue, User
)

# ----------------- CONFIGURABLE POLICIES -----------------

class APAARFormatPolicy(BaseModel):
    """Configurable format policy for APAAR IDs."""
    expected_length: int = 12
    require_numeric: bool = True
    require_verhoeff: bool = True
    format_disclaimer: str = (
        "Format and Verhoeff checksum validation confirms syntax conformity according to national schema. "
        "Format compliance does NOT prove identity authenticity in the national registry."
    )

class IntakePolicyConfig(BaseModel):
    """Configurable statutory intake limits and quota regulations."""
    tfw_quota_percent: float = 5.0          # Tuition Fee Waiver max 5% of sanctioned intake
    nri_quota_percent: float = 5.0          # NRI quota max 5% of sanctioned intake
    foreign_national_quota_percent: float = 15.0 # FN / PIO quota max 15% of sanctioned intake
    supernumerary_independent: bool = True  # Supernumerary seats do NOT consume ordinary approved intake
    active_admission_statuses: List[str] = ["ENROLLED", "ADMITTED", "PROVISIONAL"]
    inactive_admission_statuses: List[str] = ["CANCELLED", "WITHDRAWN", "COMPLETED", "SUSPENDED"]

class AnomalyPolicyConfig(BaseModel):
    """Configurable thresholds for detecting suspicious bulk changes."""
    bulk_surge_threshold_percent: float = 30.0  # Alert if batch adds > 30% of approved capacity
    batch_size_warning_threshold: int = 500

# ----------------- STRUCTURED ISSUE OUTPUT -----------------

class ValidationIssueDetail(BaseModel):
    rule_id: str
    field_name: str
    error_code: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    error_message: str
    suggested_remediation: str
    anomaly_score: float = 0.0
    is_potential_anomaly: bool = False
    entity_type: str = "ENROLMENT_RECORD"  # STUDENT_RECORD, BATCH_ROW, INTAKE_RECONCILIATION
    entity_id: Optional[str] = None
    row_number: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AnomalyRiskReport(BaseModel):
    total_score: float
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    is_potential_anomaly: bool
    triggered_rules: List[Dict[str, Any]]
    explanation: str

# ----------------- DETERMINISTIC VALIDATION SERVICE -----------------

class ValidationEngine:
    """
    Deterministic, testable core data-quality and admission-validation engine for SIH26263.
    Evaluates all 14 statutory AICTE data quality rules, intake calculations,
    conservative duplicate detection, and explainable anomaly risk scoring.
    """
    def __init__(
        self,
        apaar_policy: Optional[APAARFormatPolicy] = None,
        intake_policy: Optional[IntakePolicyConfig] = None,
        anomaly_policy: Optional[AnomalyPolicyConfig] = None
    ):
        self.apaar_policy = apaar_policy or APAARFormatPolicy()
        self.intake_policy = intake_policy or IntakePolicyConfig()
        self.anomaly_policy = anomaly_policy or AnomalyPolicyConfig()

    # ----------------- INTAKE CALCULATION -----------------

    def calculate_actual_intake(
        self,
        db: Session,
        institution_id: str,
        academic_year: str,
        course_id: Optional[str] = None,
        programme_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate actual enrolment using unique active enrolment records,
        grouped by institution, programme, and course for a given academic year.
        Strictly separates ordinary approved intake from supernumerary quotas.
        Excludes CANCELLED, WITHDRAWN, or COMPLETED admissions to prevent double-counting.
        """
        query = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == institution_id,
            StudentEnrolment.academic_year == academic_year,
            StudentEnrolment.admission_status.in_(self.intake_policy.active_admission_statuses)
        )
        if course_id:
            query = query.filter(StudentEnrolment.course_id == course_id)
        if programme_id:
            query = query.join(Course).filter(Course.programme_id == programme_id)

        active_enrolments = query.all()

        # Deduplicate by student identity to prevent duplicate counting in same course
        seen_regular_students: Set[str] = set()
        seen_supernumerary_students: Set[str] = set()
        tfw_count = 0
        nri_count = 0
        fn_count = 0

        for e in active_enrolments:
            key = f"{e.student_id}:{e.course_id}"
            if e.is_supernumerary:
                if key not in seen_supernumerary_students:
                    seen_supernumerary_students.add(key)
                    if e.supernumerary_type == "TFW":
                        tfw_count += 1
                    elif e.supernumerary_type == "NRI":
                        nri_count += 1
                    elif e.supernumerary_type in ("FOREIGN_NATIONAL", "PIO"):
                        fn_count += 1
            else:
                if key not in seen_regular_students:
                    seen_regular_students.add(key)

        return {
            "institution_id": institution_id,
            "academic_year": academic_year,
            "course_id": course_id,
            "regular_active_enrolled": len(seen_regular_students),
            "supernumerary_active_enrolled": len(seen_supernumerary_students),
            "tfw_enrolled": tfw_count,
            "nri_enrolled": nri_count,
            "fn_enrolled": fn_count,
            "total_active_students": len(seen_regular_students) + len(seen_supernumerary_students)
        }

    # ----------------- CONSERVATIVE DUPLICATE DETECTION -----------------

    def detect_conservative_duplicate_matches(
        self,
        db: Session,
        institution_id: str,
        student_name: str,
        date_of_birth: str,
        gender: Optional[str] = None,
        exclude_student_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Conservative matching on name and date of birth only to flag possible matches
        for human administrative review. Does NOT automatically merge people.
        """
        norm_name = student_name.strip().lower()
        clean_dob = date_of_birth.strip()

        candidates = db.query(Student).join(StudentEnrolment).filter(
            StudentEnrolment.institution_id == institution_id,
            func.lower(Student.student_name) == norm_name,
            Student.date_of_birth == clean_dob
        )
        if exclude_student_id:
            candidates = candidates.filter(Student.id != exclude_student_id)

        matches = []
        for c in candidates.all():
            for e in c.enrolments:
                matches.append({
                    "matched_student_id": c.id,
                    "matched_student_name": c.student_name,
                    "matched_roll_no": e.internal_student_id,
                    "matched_apaar_masked": c.apaar_masked,
                    "academic_year": e.academic_year,
                    "reason": f"Exact match on normalized name ('{c.student_name}') and date of birth ('{c.date_of_birth}')."
                })
        return matches

    # ----------------- RECORD VALIDATION (RULES 1 - 12) -----------------

    def validate_single_record(
        self,
        data: Dict[str, Any],
        db: Session,
        institution_id: str,
        academic_year: str,
        exclude_enrolment_id: Optional[str] = None,
        row_number: Optional[int] = None
    ) -> List[ValidationIssueDetail]:
        """
        Deterministically evaluates Rules 1 through 12 for an admission record.
        """
        issues: List[ValidationIssueDetail] = []

        # Extract & Clean Fields
        name = str(data.get("student_name") or "").strip()
        internal_id = normalize_identifier(data.get("internal_student_id") or data.get("internal_id") or "")
        apaar = str(data.get("apaar_id") or "").strip()
        course_in = str(data.get("course_id") or data.get("course") or "").strip()
        prog_in = str(data.get("programme_id") or data.get("programme") or "").strip()
        dob = str(data.get("date_of_birth") or "").strip()
        acad_year = str(data.get("academic_year") or academic_year).strip()
        adm_year = data.get("admission_year")
        adm_status = str(data.get("admission_status") or "ENROLLED").strip().upper()
        
        is_super = str(data.get("is_supernumerary", "FALSE")).upper() in ("TRUE", "1", "YES")
        super_type = str(data.get("supernumerary_type") or "NONE").strip().upper()
        nri = str(data.get("nri_status", "FALSE")).upper() in ("TRUE", "1", "YES")
        oci = str(data.get("oci_status", "FALSE")).upper() in ("TRUE", "1", "YES")
        fn = str(data.get("foreign_national_status", "FALSE")).upper() in ("TRUE", "1", "YES")

        # ---------------- RULE 6: MISSING MANDATORY FIELDS ----------------
        if not name:
            issues.append(ValidationIssueDetail(
                rule_id="RULE_06_MISSING_MANDATORY_FIELD",
                field_name="student_name",
                error_code="MISSING_MANDATORY_FIELD",
                severity="CRITICAL",
                error_message="Mandatory field 'student_name' is missing or blank.",
                suggested_remediation="Enter the legal full name of the student.",
                row_number=row_number,
                anomaly_score=15.0
            ))

        if not internal_id:
            issues.append(ValidationIssueDetail(
                rule_id="RULE_06_MISSING_MANDATORY_FIELD",
                field_name="internal_student_id",
                error_code="MISSING_MANDATORY_FIELD",
                severity="CRITICAL",
                error_message="Mandatory field 'internal_student_id' (Roll No) is missing or blank.",
                suggested_remediation="Provide the internal student roll number.",
                row_number=row_number,
                anomaly_score=20.0
            ))

        if not dob:
            issues.append(ValidationIssueDetail(
                rule_id="RULE_06_MISSING_MANDATORY_FIELD",
                field_name="date_of_birth",
                error_code="MISSING_MANDATORY_FIELD",
                severity="CRITICAL",
                error_message="Mandatory field 'date_of_birth' is missing or blank.",
                suggested_remediation="Specify date of birth in standard YYYY-MM-DD format.",
                row_number=row_number,
                anomaly_score=10.0
            ))

        if not course_in:
            issues.append(ValidationIssueDetail(
                rule_id="RULE_06_MISSING_MANDATORY_FIELD",
                field_name="course_id",
                error_code="MISSING_MANDATORY_FIELD",
                severity="CRITICAL",
                error_message="Mandatory field 'course' is missing or blank.",
                suggested_remediation="Allocate an approved course discipline.",
                row_number=row_number,
                anomaly_score=20.0
            ))

        # ---------------- RULE 1: MISSING APAAR ID ----------------
        if not apaar:
            issues.append(ValidationIssueDetail(
                rule_id="RULE_01_MISSING_APAAR",
                field_name="apaar_id",
                error_code="MISSING_APAAR_ID",
                severity="CRITICAL",
                error_message="Mandatory APAAR ID is missing or empty.",
                suggested_remediation="Obtain and enter the student's 12-digit national APAAR ID.",
                row_number=row_number,
                anomaly_score=30.0
            ))
        else:
            # ---------------- RULE 2: MALFORMED APAAR ID ----------------
            clean_ap = clean_apaar_id(apaar)
            is_valid_format, validated_ap, format_err = validate_apaar_format(clean_ap)
            if not is_valid_format or len(clean_ap) != self.apaar_policy.expected_length:
                issues.append(ValidationIssueDetail(
                    rule_id="RULE_02_MALFORMED_APAAR",
                    field_name="apaar_id",
                    error_code="MALFORMED_APAAR_ID",
                    severity="CRITICAL",
                    error_message=(
                        f"Malformed APAAR ID '{apaar}': {format_err or 'Invalid Verhoeff checksum'}. "
                        f"{self.apaar_policy.format_disclaimer}"
                    ),
                    suggested_remediation="Verify the 12 numeric digits against official DigiLocker / ABC identity documents.",
                    row_number=row_number,
                    anomaly_score=35.0
                ))
            else:
                ap_hash = hash_apaar_id(validated_ap)

                # ---------------- RULE 3: DUPLICATE APAAR WITHIN INSTITUTION ----------------
                q_internal_dup = db.query(StudentEnrolment).join(Student).filter(
                    Student.apaar_hash == ap_hash,
                    StudentEnrolment.institution_id == institution_id,
                    StudentEnrolment.academic_year == acad_year,
                    StudentEnrolment.admission_status.in_(self.intake_policy.active_admission_statuses)
                )
                if exclude_enrolment_id:
                    q_internal_dup = q_internal_dup.filter(StudentEnrolment.id != exclude_enrolment_id)
                internal_dup = q_internal_dup.first()

                if internal_dup:
                    issues.append(ValidationIssueDetail(
                        rule_id="RULE_03_INTERNAL_DUPLICATE_APAAR",
                        field_name="apaar_id",
                        error_code="DUPLICATE_APAAR_INTERNAL",
                        severity="CRITICAL",
                        error_message=(
                            f"Duplicate APAAR ID '{mask_apaar_id(clean_ap)}' is already assigned to active student "
                            f"'{internal_dup.student.student_name}' (Roll: {internal_dup.internal_student_id}) in this institution for session {acad_year}."
                        ),
                        suggested_remediation="Audit institutional roster to eliminate internal duplicate student profile.",
                        row_number=row_number,
                        anomaly_score=45.0,
                        metadata={"colliding_roll": internal_dup.internal_student_id}
                    ))

                # ---------------- RULE 4: CROSS-INSTITUTION DUPLICATE ENROLMENT ----------------
                q_cross_dup = db.query(StudentEnrolment).join(Student).filter(
                    Student.apaar_hash == ap_hash,
                    StudentEnrolment.institution_id != institution_id,
                    StudentEnrolment.academic_year == acad_year,
                    StudentEnrolment.admission_status.in_(self.intake_policy.active_admission_statuses)
                )
                cross_dup = q_cross_dup.first()
                if cross_dup:
                    issues.append(ValidationIssueDetail(
                        rule_id="RULE_04_CROSS_INST_DUPLICATE",
                        field_name="apaar_id",
                        error_code="CROSS_INSTITUTION_DUPLICATE",
                        severity="HIGH",
                        error_message=(
                            f"Potential anomaly: Student holding APAAR ID '{mask_apaar_id(clean_ap)}' has concurrent active enrolment "
                            f"at '{cross_dup.institution.name}' (Roll: {cross_dup.internal_student_id}) in academic session {acad_year}."
                        ),
                        suggested_remediation="Initiate central AICTE scrutiny to resolve dual admission or verify student migration clearance.",
                        row_number=row_number,
                        anomaly_score=50.0,
                        is_potential_anomaly=True,
                        metadata={
                            "other_institution": cross_dup.institution.name,
                            "other_institution_id": cross_dup.institution_id,
                            "other_roll": cross_dup.internal_student_id
                        }
                    ))

                # ---------------- RULE 12: CONFLICTING ATTRIBUTES ACROSS RECORDS ----------------
                existing_student = db.query(Student).filter(Student.apaar_hash == ap_hash).first()
                if existing_student:
                    diffs = []
                    if dob and existing_student.date_of_birth and dob != existing_student.date_of_birth:
                        diffs.append(f"Date of birth mismatch: '{dob}' vs existing '{existing_student.date_of_birth}'")
                    if name and existing_student.student_name and name.lower() != existing_student.student_name.lower():
                        diffs.append(f"Name spelling divergence: '{name}' vs existing '{existing_student.student_name}'")
                    
                    if diffs:
                        issues.append(ValidationIssueDetail(
                            rule_id="RULE_12_CONFLICTING_ATTRIBUTES",
                            field_name="student_name",
                            error_code="CONFLICTING_STUDENT_ATTRIBUTES",
                            severity="MEDIUM",
                            error_message=(
                                f"Potential anomaly: Conflicting student identity attributes detected for APAAR {mask_apaar_id(clean_ap)}: "
                                + "; ".join(diffs)
                            ),
                            suggested_remediation="Reconcile official government identity documents to harmonize divergent demographic records.",
                            row_number=row_number,
                            anomaly_score=25.0,
                            is_potential_anomaly=True
                        ))

        # ---------------- RULE 5: DUPLICATE INTERNAL STUDENT IDENTIFIER ----------------
        if internal_id:
            q_roll_dup = db.query(StudentEnrolment).filter(
                StudentEnrolment.institution_id == institution_id,
                StudentEnrolment.academic_year == acad_year,
                StudentEnrolment.internal_student_id == internal_id
            )
            if exclude_enrolment_id:
                q_roll_dup = q_roll_dup.filter(StudentEnrolment.id != exclude_enrolment_id)
            roll_dup = q_roll_dup.first()
            if roll_dup:
                issues.append(ValidationIssueDetail(
                    rule_id="RULE_05_DUPLICATE_INTERNAL_ID",
                    field_name="internal_student_id",
                    error_code="DUPLICATE_INTERNAL_ID",
                    severity="CRITICAL",
                    error_message=f"Internal student roll number '{internal_id}' is already registered in session {acad_year}.",
                    suggested_remediation="Assign a unique roll number conforming to institutional numbering scheme.",
                    row_number=row_number,
                    anomaly_score=35.0
                ))

        # ---------------- RULE 7: INVALID ACADEMIC YEAR OR STATUS ----------------
        year_pattern = r"^\d{4}-\d{4}$"
        if not re.match(year_pattern, acad_year):
            issues.append(ValidationIssueDetail(
                rule_id="RULE_07_INVALID_YEAR_OR_STATUS",
                field_name="academic_year",
                error_code="INVALID_ACADEMIC_YEAR_FORMAT",
                severity="HIGH",
                error_message=f"Academic year '{acad_year}' does not match standard YYYY-YYYY session format.",
                suggested_remediation="Specify academic session in YYYY-YYYY format (e.g. 2024-2025).",
                row_number=row_number,
                anomaly_score=15.0
            ))
        else:
            try:
                y1, y2 = [int(p) for p in acad_year.split("-")]
                if y2 != y1 + 1:
                    issues.append(ValidationIssueDetail(
                        rule_id="RULE_07_INVALID_YEAR_OR_STATUS",
                        field_name="academic_year",
                        error_code="NON_CONSECUTIVE_ACADEMIC_YEAR",
                        severity="HIGH",
                        error_message=f"Academic session '{acad_year}' spans non-consecutive years.",
                        suggested_remediation="Ensure session ends in consecutive year (e.g. 2024-2025).",
                        row_number=row_number,
                        anomaly_score=15.0
                    ))
            except Exception:
                pass

        valid_statuses = {"ENROLLED", "ADMITTED", "PROVISIONAL", "SUSPENDED", "WITHDRAWN", "CANCELLED", "COMPLETED"}
        if adm_status not in valid_statuses:
            issues.append(ValidationIssueDetail(
                rule_id="RULE_07_INVALID_YEAR_OR_STATUS",
                field_name="admission_status",
                error_code="INVALID_ADMISSION_STATUS",
                severity="HIGH",
                error_message=f"Unrecognized admission status '{adm_status}'. Allowed: {', '.join(sorted(valid_statuses))}.",
                suggested_remediation="Choose a recognized statutory admission status.",
                row_number=row_number,
                anomaly_score=10.0
            ))

        # ---------------- RULE 8: INCONSISTENT PROGRAMME / INSTITUTION RELATIONSHIP ----------------
        course_obj = None
        if course_in:
            course_obj = db.query(Course).filter(
                or_(
                    Course.id == course_in,
                    Course.code.ilike(course_in),
                    Course.name.ilike(course_in)
                )
            ).first()

            if not course_obj:
                issues.append(ValidationIssueDetail(
                    rule_id="RULE_08_INCONSISTENT_PROGRAMME",
                    field_name="course_id",
                    error_code="UNAPPROVED_COURSE",
                    severity="CRITICAL",
                    error_message=f"Course '{course_in}' does not exist in central AICTE academic catalog.",
                    suggested_remediation="Map to an approved course discipline code or title.",
                    row_number=row_number,
                    anomaly_score=25.0
                ))
            else:
                # Check programme consistency if declared
                if prog_in and course_obj.programme:
                    prog_norm = prog_in.lower().replace("_", " ").replace("&", "and")
                    curr_prog_name = course_obj.programme.name.lower().replace("_", " ").replace("&", "and")
                    curr_prog_code = course_obj.programme.code.lower().replace("_", " ").replace("&", "and")
                    if prog_norm not in curr_prog_name and prog_norm not in curr_prog_code:
                        issues.append(ValidationIssueDetail(
                            rule_id="RULE_08_INCONSISTENT_PROGRAMME",
                            field_name="programme_id",
                            error_code="INCONSISTENT_PROGRAMME_COURSE_PAIR",
                            severity="CRITICAL",
                            error_message=f"Course '{course_obj.name}' belongs to programme '{course_obj.programme.name}', inconsistent with declared '{prog_in}'.",
                            suggested_remediation="Correct programme domain to match the course curriculum.",
                            row_number=row_number,
                            anomaly_score=20.0
                        ))

        # ---------------- RULE 9 & RULE 10: INTAKE & SUPERNUMERARY POLICIES ----------------
        if course_obj and adm_status in self.intake_policy.active_admission_statuses:
            intake = db.query(InstitutionIntake).filter(
                InstitutionIntake.institution_id == institution_id,
                InstitutionIntake.course_id == course_obj.id,
                InstitutionIntake.academic_year == acad_year
            ).first()

            if intake:
                counts = self.calculate_actual_intake(db, institution_id, acad_year, course_id=course_obj.id)
                curr_reg = counts["regular_active_enrolled"]
                
                # If creating new regular admission, check if exceeds
                if not is_super:
                    # RULE 9: Admissions exceeding approved intake
                    if curr_reg >= intake.approved_intake and (not exclude_enrolment_id):
                        issues.append(ValidationIssueDetail(
                            rule_id="RULE_09_INTAKE_EXCEEDED",
                            field_name="course_id",
                            error_code="ADMISSIONS_EXCEED_APPROVED_INTAKE",
                            severity="CRITICAL",
                            error_message=(
                                f"Active regular admissions ({curr_reg}) reached or exceed sanctioned core intake "
                                f"({intake.approved_intake}) for course '{course_obj.name}' in session {acad_year}."
                            ),
                            suggested_remediation="Halt regular admissions or seek sanctioned intake revision from AICTE.",
                            row_number=row_number,
                            anomaly_score=40.0,
                            metadata={"approved_intake": intake.approved_intake, "current_enrolled": curr_reg}
                        ))
                else:
                    # RULE 10: Supernumerary admissions handled separately
                    if super_type == "TFW" and counts["tfw_enrolled"] >= intake.tfw_supernumerary_quota and (not exclude_enrolment_id):
                        issues.append(ValidationIssueDetail(
                            rule_id="RULE_10_SUPERNUMERARY_VIOLATION",
                            field_name="supernumerary_type",
                            error_code="TFW_QUOTA_CAP_EXCEEDED",
                            severity="HIGH",
                            error_message=f"TFW admissions ({counts['tfw_enrolled']}) exceed authorized quota cap ({intake.tfw_supernumerary_quota}) for '{course_obj.name}'.",
                            suggested_remediation="Verify Tuition Fee Waiver criteria compliance under state admission rules.",
                            row_number=row_number,
                            anomaly_score=25.0
                        ))
                    elif super_type in ("NRI", "FOREIGN_NATIONAL"):
                        allowed_quota = intake.nri_supernumerary_quota if super_type == "NRI" else intake.fn_supernumerary_quota
                        curr_quota_count = counts["nri_enrolled"] if super_type == "NRI" else counts["fn_enrolled"]
                        if curr_quota_count >= allowed_quota and (not exclude_enrolment_id):
                            issues.append(ValidationIssueDetail(
                                rule_id="RULE_10_SUPERNUMERARY_VIOLATION",
                                field_name="supernumerary_type",
                                error_code="INTERNATIONAL_QUOTA_CAP_EXCEEDED",
                                severity="HIGH",
                                error_message=f"{super_type} admissions ({curr_quota_count}) exceed authorized quota cap ({allowed_quota}).",
                                suggested_remediation="Supernumerary quota seats cannot exceed statutory limit.",
                                row_number=row_number,
                                anomaly_score=25.0
                            ))

        # ---------------- RULE 11: INCONSISTENT NATIONALITY & DOMICILE DATA ----------------
        if is_super and super_type == "NRI" and not nri and not oci:
            issues.append(ValidationIssueDetail(
                rule_id="RULE_11_INCONSISTENT_NATIONALITY",
                field_name="nri_status",
                error_code="INCONSISTENT_NRI_STATUS",
                severity="MEDIUM",
                error_message="Student enrolled under NRI Quota but both NRI Category and OCI Status are marked False.",
                suggested_remediation="Verify and check NRI category or OCI documentation in student profile.",
                row_number=row_number,
                anomaly_score=15.0
            ))
        elif is_super and super_type == "FOREIGN_NATIONAL" and not fn:
            issues.append(ValidationIssueDetail(
                rule_id="RULE_11_INCONSISTENT_NATIONALITY",
                field_name="foreign_national_status",
                error_code="INCONSISTENT_FOREIGN_NATIONAL_STATUS",
                severity="MEDIUM",
                error_message="Student enrolled under Foreign National Quota but Foreign National status is marked False.",
                suggested_remediation="Confirm valid foreign passport and visa details.",
                row_number=row_number,
                anomaly_score=15.0
            ))
        elif is_super and super_type == "TFW" and fn:
            issues.append(ValidationIssueDetail(
                rule_id="RULE_11_INCONSISTENT_NATIONALITY",
                field_name="foreign_national_status",
                error_code="CONTRADICTORY_TFW_FOREIGN_NATIONAL",
                severity="MEDIUM",
                error_message="TFW (Tuition Fee Waiver) quota is restricted to domestic state domicile students, but Foreign National status is marked True.",
                suggested_remediation="Review state domicile criteria before allocating TFW benefits to non-domestic students.",
                row_number=row_number,
                anomaly_score=20.0
            ))

        # Conservative match check
        if name and dob and not any(i.rule_id == "RULE_03_INTERNAL_DUPLICATE_APAAR" for i in issues):
            conservative_matches = self.detect_conservative_duplicate_matches(
                db, institution_id, name, dob, gender=data.get("gender")
            )
            for m in conservative_matches:
                if m["matched_roll_no"] != internal_id:
                    issues.append(ValidationIssueDetail(
                        rule_id="RULE_03_INTERNAL_DUPLICATE_APAAR",
                        field_name="student_name",
                        error_code="POTENTIAL_DUPLICATE_IDENTITY_MATCH",
                        severity="MEDIUM",
                        error_message=(
                            f"Potential anomaly: Conservative match on name ('{m['matched_student_name']}') and DOB ('{dob}') "
                            f"with existing Roll '{m['matched_roll_no']}'. Record is NOT merged automatically; requires human review."
                        ),
                        suggested_remediation="Review identity proof to verify whether this represents a distinct candidate or duplicate registration.",
                        row_number=row_number,
                        anomaly_score=20.0,
                        is_potential_anomaly=True,
                        metadata=m
                    ))

        return issues

    # ----------------- BATCH VALIDATION (RULES 13 & 14) -----------------

    def validate_csv_batch(
        self,
        rows: List[Dict[str, Any]],
        db: Session,
        institution_id: str,
        academic_year: str,
        filename: str = "upload.csv"
    ) -> Tuple[List[ValidationIssueDetail], AnomalyRiskReport]:
        """
        Validates an entire uploaded CSV batch:
        - Evaluates intra-batch duplicates (Rule 13).
        - Evaluates unusual bulk enrolment surges (Rule 14).
        - Evaluates record-level rules 1-12 for each row.
        - Calculates explainable anomaly risk report.
        """
        all_issues: List[ValidationIssueDetail] = []
        seen_rolls: Dict[str, int] = {}
        seen_apaars: Dict[str, int] = {}

        # ---------------- RULE 13: DUPLICATE ROWS WITHIN SINGLE UPLOAD FILE ----------------
        for idx, row in enumerate(rows, start=1):
            roll = normalize_identifier(row.get("internal_student_id") or row.get("internal_id") or "")
            apaar = clean_apaar_id(str(row.get("apaar_id") or ""))

            if roll:
                if roll in seen_rolls:
                    orig_row = seen_rolls[roll]
                    all_issues.append(ValidationIssueDetail(
                        rule_id="RULE_13_DUPLICATE_FILE_ROWS",
                        field_name="internal_student_id",
                        error_code="DUPLICATE_ROLL_IN_UPLOAD_FILE",
                        severity="CRITICAL",
                        error_message=f"Duplicate roll '{roll}' at row #{idx} was already defined at row #{orig_row} in this upload file.",
                        suggested_remediation="Remove or correct duplicate rows in CSV file before submission.",
                        row_number=idx,
                        anomaly_score=30.0,
                        metadata={"duplicate_of_row": orig_row}
                    ))
                else:
                    seen_rolls[roll] = idx

            if apaar and len(apaar) == self.apaar_policy.expected_length:
                if apaar in seen_apaars:
                    orig_row = seen_apaars[apaar]
                    all_issues.append(ValidationIssueDetail(
                        rule_id="RULE_13_DUPLICATE_FILE_ROWS",
                        field_name="apaar_id",
                        error_code="DUPLICATE_APAAR_IN_UPLOAD_FILE",
                        severity="CRITICAL",
                        error_message=f"Duplicate APAAR ID at row #{idx} was already defined at row #{orig_row} in this upload file.",
                        suggested_remediation="Ensure each row represents a unique national student identifier.",
                        row_number=idx,
                        anomaly_score=35.0,
                        metadata={"duplicate_of_row": orig_row}
                    ))
                else:
                    seen_apaars[apaar] = idx

            # Run record-level rules
            row_issues = self.validate_single_record(
                row, db, institution_id, academic_year, row_number=idx
            )
            all_issues.extend(row_issues)

        # ---------------- RULE 14: SUSPICIOUS BULK CHANGES OR SURGES ----------------
        inst = db.query(Institution).filter(Institution.id == institution_id).first()
        total_sanctioned = db.query(func.coalesce(func.sum(InstitutionIntake.approved_intake), 0)).filter(
            InstitutionIntake.institution_id == institution_id,
            InstitutionIntake.academic_year == academic_year
        ).scalar() or 0

        if total_sanctioned > 0:
            surge_pct = (len(rows) / total_sanctioned) * 100
            if surge_pct > self.anomaly_policy.bulk_surge_threshold_percent:
                all_issues.append(ValidationIssueDetail(
                    rule_id="RULE_14_SUSPICIOUS_BULK_CHANGE",
                    field_name="batch_total",
                    error_code="UNUSUAL_ENROLMENT_SURGE",
                    severity="MEDIUM",
                    error_message=(
                        f"Potential anomaly: Single batch contains {len(rows)} student admissions, "
                        f"representing +{round(surge_pct, 1)}% of total sanctioned institutional intake ({total_sanctioned} seats)."
                    ),
                    suggested_remediation="Confirm approval by institutional registrar for large one-off intake batches.",
                    anomaly_score=25.0,
                    is_potential_anomaly=True,
                    metadata={"batch_size": len(rows), "sanctioned_intake": total_sanctioned, "surge_percent": round(surge_pct, 1)}
                ))

        anomaly_report = self.calculate_anomaly_report(all_issues)
        return all_issues, anomaly_report

    # ----------------- ANOMALY ENGINE RISK SCORING -----------------

    def calculate_anomaly_report(self, issues: List[ValidationIssueDetail]) -> AnomalyRiskReport:
        """
        Deterministic, explainable risk scoring based on triggered rules.
        """
        if not issues:
            return AnomalyRiskReport(
                total_score=0.0,
                risk_level="LOW",
                is_potential_anomaly=False,
                triggered_rules=[],
                explanation="No data quality violations or anomalies detected."
            )

        total_score = min(100.0, sum(i.anomaly_score for i in issues))
        has_critical = any(i.severity == "CRITICAL" for i in issues)
        has_potential_anomaly = any(i.is_potential_anomaly for i in issues)

        if total_score >= 70.0 or (has_critical and total_score >= 50.0):
            risk_level = "CRITICAL"
        elif total_score >= 40.0:
            risk_level = "HIGH"
        elif total_score >= 20.0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        triggered = [
            {
                "rule_id": i.rule_id,
                "error_code": i.error_code,
                "severity": i.severity,
                "score_weight": i.anomaly_score,
                "explanation": i.error_message
            }
            for i in issues[:10]
        ]

        summary_text = (
            f"Evaluated {len(issues)} data quality issue(s). "
            f"Overall risk assessment: {risk_level} (Score: {round(total_score, 1)}/100). "
            + ("Potential anomaly patterns detected requiring administrative review." if has_potential_anomaly else "Statutory data quality rules triggered.")
        )

        return AnomalyRiskReport(
            total_score=round(total_score, 1),
            risk_level=risk_level,
            is_potential_anomaly=has_potential_anomaly,
            triggered_rules=triggered,
            explanation=summary_text
        )

    # ----------------- SYSTEM-WIDE RECONCILIATION AUDIT -----------------

    def audit_institution(
        self,
        db: Session,
        institution_id: str,
        academic_year: str = "2024-2025"
    ) -> List[ValidationIssueDetail]:
        """
        Run full 14-rule audit scan across all persistent student enrolments
        and intake limits for a given institution.
        """
        issues: List[ValidationIssueDetail] = []
        enrolments = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == institution_id,
            StudentEnrolment.academic_year == academic_year
        ).all()

        for e in enrolments:
            payload = {
                "student_name": e.student.student_name if e.student else "",
                "internal_student_id": e.internal_student_id,
                "apaar_id": e.student.apaar_id_encrypted if e.student else "",
                "course_id": e.course_id,
                "programme_id": e.course.programme_id if e.course else None,
                "date_of_birth": e.student.date_of_birth if e.student else "",
                "academic_year": e.academic_year,
                "admission_year": e.admission_year,
                "admission_status": e.admission_status,
                "is_supernumerary": e.is_supernumerary,
                "supernumerary_type": e.supernumerary_type,
                "nri_status": e.nri_status,
                "oci_status": e.oci_status,
                "foreign_national_status": e.foreign_national_status
            }
            rec_issues = self.validate_single_record(
                payload, db, institution_id, academic_year, exclude_enrolment_id=e.id
            )
            for iss in rec_issues:
                iss.entity_id = e.id
                iss.metadata["internal_roll"] = e.internal_student_id
                iss.metadata["student_name"] = e.student.student_name if e.student else ""
            issues.extend(rec_issues)

        return issues
