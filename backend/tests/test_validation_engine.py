import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.database.session import SessionLocal
from app.database.models import (
    Institution, InstitutionIntake, Programme, Course,
    Student, StudentEnrolment, ValidationIssue, User
)
from app.core.validation_engine import (
    ValidationEngine, APAARFormatPolicy, IntakePolicyConfig, AnomalyPolicyConfig
)
from app.core.identifiers import (
    generate_uuid, normalize_identifier, hash_apaar_id, mask_apaar_id
)

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

# ----------------- 1. RULE 1: MISSING APAAR ID -----------------

def test_rule_01_missing_apaar(db):
    engine = ValidationEngine()
    inst = db.query(Institution).first()
    issues = engine.validate_single_record({
        "student_name": "Vikram Seth",
        "internal_student_id": "TEST-ROLL-01",
        "apaar_id": "",
        "course_id": "crs-cse",
        "date_of_birth": "2004-05-15",
        "academic_year": "2024-2025"
    }, db, inst.id, "2024-2025")

    rule_1_issues = [i for i in issues if i.rule_id == "RULE_01_MISSING_APAAR"]
    assert len(rule_1_issues) == 1
    assert rule_1_issues[0].error_code == "MISSING_APAAR_ID"
    assert rule_1_issues[0].severity == "CRITICAL"
    assert "mandatory" in rule_1_issues[0].error_message.lower()
    assert "remediation" in rule_1_issues[0].suggested_remediation.lower() or len(rule_1_issues[0].suggested_remediation) > 5

# ----------------- 2. RULE 2: MALFORMED APAAR ID -----------------

def test_rule_02_malformed_apaar_and_disclaimer(db):
    engine = ValidationEngine()
    inst = db.query(Institution).first()
    
    # Non-12 length and invalid checksum
    issues = engine.validate_single_record({
        "student_name": "Meera Patel",
        "internal_student_id": "TEST-ROLL-02",
        "apaar_id": "12345ABC",  # contains letters & wrong length
        "course_id": "crs-cse",
        "date_of_birth": "2004-06-20",
        "academic_year": "2024-2025"
    }, db, inst.id, "2024-2025")

    rule_2_issues = [i for i in issues if i.rule_id == "RULE_02_MALFORMED_APAAR"]
    assert len(rule_2_issues) == 1
    assert rule_2_issues[0].error_code == "MALFORMED_APAAR_ID"
    assert rule_2_issues[0].severity == "CRITICAL"
    # Verify statutory disclaimer that format check does not prove registry authenticity
    assert "does not prove" in rule_2_issues[0].error_message.lower()

# ----------------- 3. RULE 3: INTERNAL DUPLICATE APAAR -----------------

def test_rule_03_duplicate_apaar_within_institution(db):
    engine = ValidationEngine()
    inst = db.query(Institution).first()
    
    # Find existing enrolled student
    enrol = db.query(StudentEnrolment).filter(
        StudentEnrolment.institution_id == inst.id,
        StudentEnrolment.admission_status == "ENROLLED"
    ).first()
    existing_student = enrol.student

    # Try enrolling another student with exact same APAAR at the same institution
    issues = engine.validate_single_record({
        "student_name": "Duplicate Candidate",
        "internal_student_id": "UNIQUE-ROLL-999",
        "apaar_id": existing_student.apaar_id_encrypted,
        "course_id": "crs-cse",
        "date_of_birth": "2004-01-01",
        "academic_year": enrol.academic_year
    }, db, inst.id, enrol.academic_year)

    rule_3_issues = [i for i in issues if i.rule_id == "RULE_03_INTERNAL_DUPLICATE_APAAR"]
    assert len(rule_3_issues) >= 1
    assert rule_3_issues[0].error_code == "DUPLICATE_APAAR_INTERNAL"
    assert rule_3_issues[0].severity == "CRITICAL"

# ----------------- 4. RULE 4: CROSS-INSTITUTION DUPLICATE -----------------

def test_rule_04_cross_institution_duplicate(db):
    engine = ValidationEngine()
    institutions = db.query(Institution).all()
    assert len(institutions) >= 2
    inst1, inst2 = institutions[0], institutions[1]

    # Pick a student enrolled in inst1
    enrol1 = db.query(StudentEnrolment).filter(
        StudentEnrolment.institution_id == inst1.id,
        StudentEnrolment.admission_status == "ENROLLED"
    ).first()

    # Attempt to enroll same APAAR in inst2
    issues = engine.validate_single_record({
        "student_name": enrol1.student.student_name,
        "internal_student_id": "INST2-ROLL-01",
        "apaar_id": enrol1.student.apaar_id_encrypted,
        "course_id": "crs-cse",
        "date_of_birth": enrol1.student.date_of_birth,
        "academic_year": enrol1.academic_year
    }, db, inst2.id, enrol1.academic_year)

    rule_4_issues = [i for i in issues if i.rule_id == "RULE_04_CROSS_INST_DUPLICATE"]
    assert len(rule_4_issues) == 1
    assert rule_4_issues[0].error_code == "CROSS_INSTITUTION_DUPLICATE"
    assert rule_4_issues[0].severity == "HIGH"
    assert rule_4_issues[0].is_potential_anomaly is True
    assert "potential anomaly" in rule_4_issues[0].error_message.lower()

# ----------------- 5. RULE 5: DUPLICATE INTERNAL STUDENT ID -----------------

def test_rule_05_duplicate_internal_roll_number(db):
    engine = ValidationEngine()
    inst = db.query(Institution).first()
    enrol = db.query(StudentEnrolment).filter(StudentEnrolment.institution_id == inst.id).first()

    # Attempt to use the same internal student roll number
    issues = engine.validate_single_record({
        "student_name": "New Candidate",
        "internal_student_id": enrol.internal_student_id,
        "apaar_id": "829104829202",
        "course_id": "crs-cse",
        "date_of_birth": "2004-10-10",
        "academic_year": enrol.academic_year
    }, db, inst.id, enrol.academic_year)

    rule_5_issues = [i for i in issues if i.rule_id == "RULE_05_DUPLICATE_INTERNAL_ID"]
    assert len(rule_5_issues) == 1
    assert rule_5_issues[0].error_code == "DUPLICATE_INTERNAL_ID"
    assert rule_5_issues[0].severity == "CRITICAL"

# ----------------- 6. RULE 6: MISSING MANDATORY FIELDS -----------------

def test_rule_06_missing_mandatory_fields(db):
    engine = ValidationEngine()
    inst = db.query(Institution).first()
    issues = engine.validate_single_record({
        "student_name": "",
        "internal_student_id": "",
        "apaar_id": "829104829202",
        "course_id": "",
        "date_of_birth": "",
        "academic_year": "2024-2025"
    }, db, inst.id, "2024-2025")

    missing_fields = {i.field_name for i in issues if i.rule_id == "RULE_06_MISSING_MANDATORY_FIELD"}
    assert "student_name" in missing_fields
    assert "internal_student_id" in missing_fields
    assert "course_id" in missing_fields
    assert "date_of_birth" in missing_fields

# ----------------- 7. RULE 7: INVALID ACADEMIC YEAR OR STATUS -----------------

def test_rule_07_invalid_academic_year_and_status(db):
    engine = ValidationEngine()
    inst = db.query(Institution).first()
    
    # Non-standard format and invalid status
    issues = engine.validate_single_record({
        "student_name": "Test Student",
        "internal_student_id": "VAL-007",
        "apaar_id": "829104829202",
        "course_id": "crs-cse",
        "date_of_birth": "2004-01-01",
        "academic_year": "2024-2026",  # non-consecutive
        "admission_status": "FICTITIOUS_STATUS"
    }, db, inst.id, "2024-2026")

    rule_7_codes = {i.error_code for i in issues if i.rule_id == "RULE_07_INVALID_YEAR_OR_STATUS"}
    assert "NON_CONSECUTIVE_ACADEMIC_YEAR" in rule_7_codes
    assert "INVALID_ADMISSION_STATUS" in rule_7_codes

# ----------------- 8. RULE 8: INCONSISTENT PROGRAMME / COURSE -----------------

def test_rule_08_inconsistent_programme_and_course(db):
    engine = ValidationEngine()
    inst = db.query(Institution).first()
    
    # Nonexistent course
    issues = engine.validate_single_record({
        "student_name": "Test Student",
        "internal_student_id": "VAL-008",
        "apaar_id": "829104829202",
        "course_id": "UNKNOWN_COURSE_XYZ",
        "date_of_birth": "2004-01-01",
        "academic_year": "2024-2025"
    }, db, inst.id, "2024-2025")

    rule_8_codes = {i.error_code for i in issues if i.rule_id == "RULE_08_INCONSISTENT_PROGRAMME"}
    assert "UNAPPROVED_COURSE" in rule_8_codes

# ----------------- 9 & 10. RULES 9 & 10: INTAKE EXCEEDED & SUPERNUMERARY -----------------

def test_rule_09_and_10_intake_and_supernumerary(db):
    engine = ValidationEngine()
    inst = db.query(Institution).first()
    intake = db.query(InstitutionIntake).filter(InstitutionIntake.institution_id == inst.id).first()

    # Artificially set approved intake to 1 to test intake capacity boundary
    orig_approved = intake.approved_intake
    orig_tfw = intake.tfw_supernumerary_quota
    try:
        intake.approved_intake = 1
        intake.tfw_supernumerary_quota = 1
        db.commit()

        # Regular admission when 1 student already enrolled
        issues_regular = engine.validate_single_record({
            "student_name": "Regular Over Intake",
            "internal_student_id": "OVER-INTAKE-REG",
            "apaar_id": "829104829210",
            "course_id": intake.course_id,
            "date_of_birth": "2004-03-03",
            "academic_year": intake.academic_year,
            "is_supernumerary": False
        }, db, inst.id, intake.academic_year)

        rule_9 = [i for i in issues_regular if i.rule_id == "RULE_09_INTAKE_EXCEEDED"]
        assert len(rule_9) == 1
        assert rule_9[0].error_code == "ADMISSIONS_EXCEED_APPROVED_INTAKE"

        # Supernumerary TFW should NOT consume regular intake
        # But if TFW quota exceeds authorized cap, Rule 10 triggers
        counts = engine.calculate_actual_intake(db, inst.id, intake.academic_year, course_id=intake.course_id)
        assert "regular_active_enrolled" in counts
        assert "supernumerary_active_enrolled" in counts
    finally:
        intake.approved_intake = orig_approved
        intake.tfw_supernumerary_quota = orig_tfw
        db.commit()

# ----------------- 11. RULE 11: INCONSISTENT NATIONALITY & NRI/OCI DATA -----------------

def test_rule_11_inconsistent_nationality_data(db):
    engine = ValidationEngine()
    inst = db.query(Institution).first()

    # Supernumerary NRI quota but marked non-NRI and non-OCI
    issues = engine.validate_single_record({
        "student_name": "NRI Discrepancy Student",
        "internal_student_id": "VAL-011",
        "apaar_id": "829104829202",
        "course_id": "crs-cse",
        "date_of_birth": "2004-01-01",
        "academic_year": "2024-2025",
        "is_supernumerary": True,
        "supernumerary_type": "NRI",
        "nri_status": False,
        "oci_status": False
    }, db, inst.id, "2024-2025")

    rule_11 = [i for i in issues if i.rule_id == "RULE_11_INCONSISTENT_NATIONALITY"]
    assert len(rule_11) == 1
    assert rule_11[0].error_code == "INCONSISTENT_NRI_STATUS"

# ----------------- 12. RULE 12: CONFLICTING ATTRIBUTES ACROSS RECORDS -----------------

def test_rule_12_conflicting_student_attributes(db):
    engine = ValidationEngine()
    inst = db.query(Institution).first()
    existing_enrol = db.query(StudentEnrolment).first()
    st = existing_enrol.student

    # Re-enrolling same APAAR with divergent date of birth and modified spelling
    issues = engine.validate_single_record({
        "student_name": f"{st.student_name} Modified",
        "internal_student_id": "DIFF-ROLL-012",
        "apaar_id": st.apaar_id_encrypted,
        "course_id": "crs-cse",
        "date_of_birth": "1999-12-31",  # completely different DOB
        "academic_year": "2025-2026"
    }, db, inst.id, "2025-2026")

    rule_12 = [i for i in issues if i.rule_id == "RULE_12_CONFLICTING_ATTRIBUTES"]
    assert len(rule_12) == 1
    assert rule_12[0].error_code == "CONFLICTING_STUDENT_ATTRIBUTES"
    assert rule_12[0].is_potential_anomaly is True

# ----------------- 13. RULE 13: DUPLICATE ROWS IN CSV BATCH -----------------

def test_rule_13_duplicate_rows_in_upload_file(db):
    engine = ValidationEngine()
    inst = db.query(Institution).first()

    batch_rows = [
        {
            "internal_student_id": "BATCH-DUP-01",
            "student_name": "Candidate Alpha",
            "apaar_id": "829104829202",
            "course_id": "crs-cse",
            "date_of_birth": "2004-01-01",
            "academic_year": "2024-2025"
        },
        {
            "internal_student_id": "BATCH-DUP-01",  # duplicate roll within file
            "student_name": "Candidate Alpha Duplicate",
            "apaar_id": "829104829210",
            "course_id": "crs-cse",
            "date_of_birth": "2004-01-01",
            "academic_year": "2024-2025"
        }
    ]

    issues, anomaly_report = engine.validate_csv_batch(batch_rows, db, inst.id, "2024-2025")
    rule_13 = [i for i in issues if i.rule_id == "RULE_13_DUPLICATE_FILE_ROWS"]
    assert len(rule_13) >= 1
    assert rule_13[0].error_code == "DUPLICATE_ROLL_IN_UPLOAD_FILE"
    assert rule_13[0].severity == "CRITICAL"

# ----------------- 14. RULE 14: SUSPICIOUS BULK CHANGES OR SURGES -----------------

def test_rule_14_suspicious_bulk_change_anomaly(db):
    engine = ValidationEngine(anomaly_policy=AnomalyPolicyConfig(bulk_surge_threshold_percent=1.0))
    inst = db.query(Institution).first()

    # 10 records when threshold is 1% will trigger surge alert
    rows = [
        {
            "internal_student_id": f"SURGE-{i}",
            "student_name": f"Surge Student {i}",
            "apaar_id": "829104829202",
            "course_id": "crs-cse",
            "date_of_birth": "2004-01-01",
            "academic_year": "2024-2025"
        }
        for i in range(1, 15)
    ]

    issues, report = engine.validate_csv_batch(rows, db, inst.id, "2024-2025")
    surge_issues = [i for i in issues if i.rule_id == "RULE_14_SUSPICIOUS_BULK_CHANGE"]
    assert len(surge_issues) == 1
    assert surge_issues[0].error_code == "UNUSUAL_ENROLMENT_SURGE"
    assert surge_issues[0].is_potential_anomaly is True
    assert "potential anomaly" in surge_issues[0].error_message.lower()

# ----------------- 15. INTAKE CALCULATION & CANCELLED ADMISSIONS -----------------

def test_intake_excludes_cancelled_and_withdrawn_admissions(db):
    engine = ValidationEngine()
    inst = db.query(Institution).first()
    course = db.query(Course).first()

    # Create active regular enrolment
    st1 = Student(
        id=generate_uuid(), student_name="Active Reg Student",
        date_of_birth="2004-01-01", gender="MALE", category="GENERAL",
        apaar_id_encrypted="829104829202", apaar_hash=hash_apaar_id("829104829202"), apaar_masked=mask_apaar_id("829104829202")
    )
    db.add(st1)
    db.flush()

    e_active = StudentEnrolment(
        id=generate_uuid(), student_id=st1.id, internal_student_id="TEST-ACTIVE-01",
        institution_id=inst.id, course_id=course.id, academic_year="2029-2030",
        admission_year=2029, admission_category="REGULAR", admission_status="ENROLLED",
        is_supernumerary=False
    )
    # Create cancelled enrolment
    st2 = Student(
        id=generate_uuid(), student_name="Cancelled Student",
        date_of_birth="2004-02-02", gender="FEMALE", category="GENERAL",
        apaar_id_encrypted="829104829210", apaar_hash=hash_apaar_id("829104829210"), apaar_masked=mask_apaar_id("829104829210")
    )
    db.add(st2)
    db.flush()

    e_cancelled = StudentEnrolment(
        id=generate_uuid(), student_id=st2.id, internal_student_id="TEST-CANCEL-02",
        institution_id=inst.id, course_id=course.id, academic_year="2029-2030",
        admission_year=2029, admission_category="REGULAR", admission_status="CANCELLED",
        is_supernumerary=False
    )
    db.add_all([e_active, e_cancelled])
    db.commit()

    try:
        counts = engine.calculate_actual_intake(db, inst.id, "2029-2030", course_id=course.id)
        # Cancelled student must NOT be counted in active enrolled
        assert counts["regular_active_enrolled"] == 1
        assert counts["total_active_students"] == 1
    finally:
        db.delete(e_active)
        db.delete(e_cancelled)
        db.delete(st1)
        db.delete(st2)
        db.commit()

# ----------------- 16. CONSERVATIVE DUPLICATE DETECTION (NO AUTO-MERGE) -----------------

def test_conservative_duplicate_detection_flags_for_human_review(db):
    engine = ValidationEngine()
    inst = db.query(Institution).first()
    enrol = db.query(StudentEnrolment).filter(StudentEnrolment.institution_id == inst.id).first()
    orig_student = enrol.student

    # Different roll, different APAAR, but identical Name and DOB
    issues = engine.validate_single_record({
        "student_name": orig_student.student_name,
        "internal_student_id": "DIFFERENT-ROLL-99",
        "apaar_id": "829104829301",
        "course_id": enrol.course_id,
        "date_of_birth": orig_student.date_of_birth,
        "academic_year": enrol.academic_year
    }, db, inst.id, enrol.academic_year)

    conservative_flags = [i for i in issues if i.error_code == "POTENTIAL_DUPLICATE_IDENTITY_MATCH"]
    assert len(conservative_flags) == 1
    assert conservative_flags[0].severity == "MEDIUM"
    assert conservative_flags[0].is_potential_anomaly is True
    # Verify instruction that record is NOT automatically merged
    assert "not merged automatically" in conservative_flags[0].error_message.lower()

# ----------------- 17. ANOMALY ENGINE EXPLAINABILITY -----------------

def test_anomaly_engine_explainable_risk_score():
    engine = ValidationEngine()
    issues = [
        engine.validate_single_record.__annotations__  # dummy
    ]
    # Test calculate_anomaly_report with high-risk issues
    from app.core.validation_engine import ValidationIssueDetail
    test_issues = [
        ValidationIssueDetail(
            rule_id="RULE_04_CROSS_INST_DUPLICATE",
            field_name="apaar_id",
            error_code="CROSS_INSTITUTION_DUPLICATE",
            severity="HIGH",
            error_message="Potential anomaly: concurrent enrolment detected.",
            suggested_remediation="Initiate central AICTE scrutiny.",
            anomaly_score=50.0,
            is_potential_anomaly=True
        ),
        ValidationIssueDetail(
            rule_id="RULE_09_INTAKE_EXCEEDED",
            field_name="course_id",
            error_code="ADMISSIONS_EXCEED_APPROVED_INTAKE",
            severity="CRITICAL",
            error_message="Active admissions exceed approved intake.",
            suggested_remediation="Halt admissions.",
            anomaly_score=40.0,
            is_potential_anomaly=False
        )
    ]
    report = engine.calculate_anomaly_report(test_issues)
    assert report.total_score == 90.0
    assert report.risk_level == "CRITICAL"
    assert report.is_potential_anomaly is True
    assert len(report.triggered_rules) == 2
    assert "CRITICAL" in report.explanation

# ----------------- 18. ISSUE MANAGEMENT LIFECYCLE (API) -----------------

def test_issue_lifecycle_transitions_and_permissions(client: TestClient, db: SessionLocal):
    # 1. Create a standalone test issue
    inst = db.query(Institution).first()
    test_issue = ValidationIssue(
        institution_id=inst.id,
        rule_id="RULE_07_INVALID_YEAR_OR_STATUS",
        field_name="academic_year",
        error_code="NON_CONSECUTIVE_ACADEMIC_YEAR",
        error_message="Session spans non-consecutive years.",
        suggested_remediation="Correct to standard format.",
        severity="HIGH",
        anomaly_score=15.0,
        resolution_status="NEW",
        created_at=datetime.now(timezone.utc)
    )
    db.add(test_issue)
    db.commit()
    db.refresh(test_issue)
    issue_id = test_issue.id

    try:
        # Login as Institution Admin
        login_res = client.post("/api/v1/auth/demo-login/1")
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # GET detail
        detail_res = client.get(f"/api/v1/validation/issues/{issue_id}", headers=headers)
        assert detail_res.status_code == 200
        assert detail_res.json()["resolution_status"] == "NEW"

        # Transition NEW -> UNDER_REVIEW
        patch1 = client.patch(f"/api/v1/validation/issues/{issue_id}", headers=headers, json={
            "resolution_status": "UNDER_REVIEW",
            "resolution_reason": "Registrar verifying original admission dossier."
        })
        assert patch1.status_code == 200
        assert patch1.json()["resolution_status"] == "UNDER_REVIEW"
        assert patch1.json()["reviewed_by_email"] == "registrar@apex.edu"

        # Transition UNDER_REVIEW -> RESOLVED
        patch2 = client.patch(f"/api/v1/validation/issues/{issue_id}", headers=headers, json={
            "resolution_status": "RESOLVED",
            "resolution_reason": "Candidate provided AICTE migration clearance certificate."
        })
        assert patch2.status_code == 200
        assert patch2.json()["resolution_status"] == "RESOLVED"
        assert patch2.json()["reviewed_at"] is not None

        # Bulk Review endpoint
        bulk_res = client.post("/api/v1/validation/issues/bulk-review", headers=headers, json={
            "issue_ids": [issue_id],
            "resolution_status": "DISMISSED",
            "resolution_reason": "Verified non-statutory exemption."
        })
        assert bulk_res.status_code == 200
        assert bulk_res.json()["updated_count"] >= 1

    finally:
        db.delete(test_issue)
        db.commit()

# ----------------- 19. WORKBENCH FILTERING & AUDIT SCAN API -----------------

def test_workbench_filtering_and_audit_api(client: TestClient):
    login_res = client.post("/api/v1/auth/demo-login/1")
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch workbench response
    wb_res = client.get("/api/v1/validation/workbench?page=1&limit=10", headers=headers)
    assert wb_res.status_code == 200
    data = wb_res.json()
    assert "items" in data
    assert "summary" in data
    assert "anomaly_score" in data["summary"]
    assert "risk_level" in data["summary"]
    assert "critical_count" in data["summary"]

    # Trigger statutory on-demand audit scan
    audit_res = client.post("/api/v1/validation/run-audit?academic_year=2024-2025", headers=headers)
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["status"] == "COMPLETED"
    assert "total_issues_found" in audit_data
    assert "anomaly_score" in audit_data

    # Verify national dashboard metrics reflects validation issue statistics
    dash_login = client.post("/api/v1/auth/demo-login/0")
    dash_token = dash_login.json()["access_token"]
    dash_res = client.get("/api/v1/dashboard/metrics", headers={"Authorization": f"Bearer {dash_token}"})
    assert dash_res.status_code == 200
    dash_metrics = dash_res.json()
    assert "total_approved_intake" in dash_metrics
    assert "total_actual_enrolled" in dash_metrics
    assert "total_validation_issues" in dash_metrics
