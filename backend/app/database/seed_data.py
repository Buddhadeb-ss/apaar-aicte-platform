import uuid
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from .models import (
    Institution, User, Programme, Course, InstitutionIntake,
    Student, StudentEnrolment, SignedCredential, ConsentRecord,
    AuditEvent, BulkUploadJob, ValidationIssue, VerificationRequest
)
from ..core.security import hash_password, generate_credential_signature
from ..core.identifiers import (
    generate_uuid, normalize_identifier, calculate_verhoeff_checksum,
    clean_apaar_id, mask_apaar_id, hash_apaar_id
)
from ..core.validation_engine import ValidationEngine

def make_valid_apaar(base_11_digits: str) -> str:
    """Generate a valid 12-digit APAAR with correct Verhoeff checksum digit."""
    c = calculate_verhoeff_checksum(base_11_digits)
    return f"{base_11_digits}{c}"

def seed_database(db: Session, force_reset: bool = False):
    """Seed relational database with realistic AICTE technical institutions and students."""
    if not force_reset and db.query(Institution).first():
        return

    # Clear existing if force reset
    if force_reset:
        db.query(ValidationIssue).delete()
        db.query(BulkUploadJob).delete()
        db.query(AuditEvent).delete()
        db.query(ConsentRecord).delete()
        db.query(SignedCredential).delete()
        db.query(StudentEnrolment).delete()
        db.query(Student).delete()
        db.query(InstitutionIntake).delete()
        db.query(Course).delete()
        db.query(Programme).delete()
        db.query(User).delete()
        db.query(Institution).delete()
        db.commit()

    # 1. Programmes
    prog_eng = Programme(
        id="PROG-ENG-TECH",
        code="ENG_TECH",
        name="Engineering & Technology",
        level="UNDERGRADUATE",
        duration_years=4
    )
    prog_mgmt = Programme(
        id="PROG-MGMT",
        code="MGMT",
        name="Management",
        level="POSTGRADUATE",
        duration_years=2
    )
    prog_pharm = Programme(
        id="PROG-PHARM",
        code="PHARM",
        name="Pharmacy",
        level="UNDERGRADUATE",
        duration_years=4
    )
    db.add_all([prog_eng, prog_mgmt, prog_pharm])
    db.flush()

    # 2. Courses
    courses = [
        Course(id="CRS-CSE", programme_id="PROG-ENG-TECH", code="CSE", name="Computer Science & Engineering", degree="B.Tech"),
        Course(id="CRS-AIDS", programme_id="PROG-ENG-TECH", code="AI_DS", name="Artificial Intelligence & Data Science", degree="B.Tech"),
        Course(id="CRS-ECE", programme_id="PROG-ENG-TECH", code="ECE", name="Electronics & Telecommunication", degree="B.Tech"),
        Course(id="CRS-IT", programme_id="PROG-ENG-TECH", code="IT", name="Information Technology", degree="B.Tech"),
        Course(id="CRS-MECH", programme_id="PROG-ENG-TECH", code="MECH", name="Mechanical Engineering", degree="B.Tech"),
        Course(id="CRS-MBA", programme_id="PROG-MGMT", code="MBA", name="Master of Business Administration", degree="MBA")
    ]
    db.add_all(courses)
    db.flush()

    # 3. Institutions
    apex = Institution(
        id="inst-apex-1001",
        aicte_permanent_id="1-4928172631",
        name="Apex Institute of Technology",
        state="Maharashtra",
        district="Pune",
        address="Sector 29, Hinjawadi Phase 1, Pune - 411057",
        institution_type="PRIVATE_UNAIDED",
        approval_session="2024-2025",
        contact_email="registrar@apex.edu",
        contact_phone="+91-20-27498100"
    )
    beacon = Institution(
        id="inst-beacon-2002",
        aicte_permanent_id="1-7719283419",
        name="Beacon College of Engineering",
        state="Karnataka",
        district="Bengaluru Urban",
        address="Kengeri Satellite Town, Outer Ring Road, Bengaluru - 560060",
        institution_type="GOVERNMENT_AIDED",
        approval_session="2024-2025",
        contact_email="principal@beacon.ac.in",
        contact_phone="+91-80-28489200"
    )
    zenith = Institution(
        id="inst-zenith-3003",
        aicte_permanent_id="1-8827361920",
        name="Zenith National Institute of Technology",
        state="Delhi",
        district="South West Delhi",
        address="Institutional Area, Sector 9, Dwarka, New Delhi - 110077",
        institution_type="DEEMED_UNIVERSITY",
        approval_session="2024-2025",
        contact_email="dean@zenith.ac.in",
        contact_phone="+91-11-25081190"
    )
    db.add_all([apex, beacon, zenith])
    db.flush()

    # 4. Institution Sanctioned Intakes (Separated strictly from student records)
    intakes = [
        # Apex Courses
        InstitutionIntake(
            institution_id="inst-apex-1001", programme_id="PROG-ENG-TECH", course_id="CRS-CSE",
            academic_year="2024-2025", approved_intake=120, tfw_supernumerary_quota=6,
            nri_supernumerary_quota=6, fn_supernumerary_quota=18, status="APPROVED"
        ),
        InstitutionIntake(
            institution_id="inst-apex-1001", programme_id="PROG-ENG-TECH", course_id="CRS-AIDS",
            academic_year="2024-2025", approved_intake=60, tfw_supernumerary_quota=3,
            nri_supernumerary_quota=3, fn_supernumerary_quota=9, status="APPROVED"
        ),
        InstitutionIntake(
            institution_id="inst-apex-1001", programme_id="PROG-ENG-TECH", course_id="CRS-ECE",
            academic_year="2024-2025", approved_intake=60, tfw_supernumerary_quota=3,
            nri_supernumerary_quota=3, fn_supernumerary_quota=9, status="APPROVED"
        ),
        InstitutionIntake(
            institution_id="inst-apex-1001", programme_id="PROG-MGMT", course_id="CRS-MBA",
            academic_year="2024-2025", approved_intake=60, tfw_supernumerary_quota=3,
            nri_supernumerary_quota=0, fn_supernumerary_quota=0, status="APPROVED"
        ),

        # Beacon Courses
        InstitutionIntake(
            institution_id="inst-beacon-2002", programme_id="PROG-ENG-TECH", course_id="CRS-IT",
            academic_year="2024-2025", approved_intake=60, tfw_supernumerary_quota=3,
            nri_supernumerary_quota=3, fn_supernumerary_quota=9, status="APPROVED"
        ),
        InstitutionIntake(
            institution_id="inst-beacon-2002", programme_id="PROG-ENG-TECH", course_id="CRS-MECH",
            academic_year="2024-2025", approved_intake=60, tfw_supernumerary_quota=3,
            nri_supernumerary_quota=0, fn_supernumerary_quota=0, status="APPROVED"
        ),

        # Zenith Courses
        InstitutionIntake(
            institution_id="inst-zenith-3003", programme_id="PROG-ENG-TECH", course_id="CRS-CSE",
            academic_year="2024-2025", approved_intake=180, tfw_supernumerary_quota=9,
            nri_supernumerary_quota=9, fn_supernumerary_quota=27, status="APPROVED"
        )
    ]
    db.add_all(intakes)
    db.flush()

    # 5. Core Student Identities & Separate Enrolments
    # Model student Aarav Sharma with stable UUID
    student_aarav_id = "stud-uuid-aarav-sharma-2024"
    aarav_apaar = make_valid_apaar("82910482916")
    aarav_student = Student(
        id=student_aarav_id,
        student_name="Aarav Sharma",
        date_of_birth="2004-05-12",
        gender="MALE",
        category="GENERAL",
        apaar_id_encrypted=aarav_apaar,
        apaar_hash=hash_apaar_id(aarav_apaar),
        apaar_masked=mask_apaar_id(aarav_apaar)
    )
    db.add(aarav_student)
    db.flush()

    # Aarav's Enrolment at Apex Institute of Technology
    enrol_aarav_id = "enrol-uuid-aarav-apex-cse"
    verif_token_aarav = "token-aarav-verified-2024"
    sig_aarav = generate_credential_signature(verif_token_aarav, "AIT-2024-CSE-007", aarav_student.apaar_hash, "inst-apex-1001")
    
    enrol_aarav = StudentEnrolment(
        id=enrol_aarav_id,
        student_id=student_aarav_id,
        internal_student_id="AIT-2024-CSE-007",
        institution_id="inst-apex-1001",
        course_id="CRS-CSE",
        academic_year="2024-2025",
        admission_year=2024,
        admission_category="REGULAR",
        is_supernumerary=False,
        supernumerary_type="NONE",
        admission_status="ENROLLED",
        record_status="ACCEPTED"
    )
    db.add(enrol_aarav)
    db.flush()

    # Aarav's Signed Credential & Consent Record
    cred_aarav = SignedCredential(
        id=generate_uuid(),
        student_id=student_aarav_id,
        enrolment_id=enrol_aarav_id,
        verification_token=verif_token_aarav,
        signature_algorithm="HMAC-SHA256",
        signature_value=sig_aarav
    )
    consent_aarav = ConsentRecord(
        id=generate_uuid(),
        student_id=student_aarav_id,
        purpose="National Academic Depository & Authorized Background Verification",
        status="GRANTED"
    )
    db.add_all([cred_aarav, consent_aarav])

    # 6. Additional Realistic Students & Enrolments
    synthetic_students = [
        ("stud-01", "Rohan Mehta", "2004-03-14", "MALE", "GENERAL", "AIT-2024-CSE-001", "inst-apex-1001", "CRS-CSE", False, "NONE", "82910482910"),
        ("stud-02", "Ananya Iyer", "2004-07-22", "FEMALE", "OBC", "AIT-2024-CSE-002", "inst-apex-1001", "CRS-CSE", False, "NONE", "82910482911"),
        ("stud-03", "Zaid Khan", "2004-01-09", "MALE", "GENERAL", "AIT-2024-CSE-003", "inst-apex-1001", "CRS-CSE", True, "TFW", "82910482912"),
        ("stud-04", "Meera Kulkarni", "2004-11-30", "FEMALE", "SC", "AIT-2024-CSE-004", "inst-apex-1001", "CRS-CSE", False, "NONE", "82910482913"),
        ("stud-05", "Devansh Patel", "2003-09-18", "MALE", "EWS", "AIT-2024-CSE-005", "inst-apex-1001", "CRS-CSE", False, "NONE", "82910482914"),
        ("stud-06", "Tanya Sen", "2004-04-05", "FEMALE", "GENERAL", "AIT-2024-CSE-006", "inst-apex-1001", "CRS-CSE", True, "NRI", "82910482915"),
        ("stud-08", "Kavya Nambiar", "2004-08-25", "FEMALE", "OBC", "AIT-2024-CSE-008", "inst-apex-1001", "CRS-CSE", False, "NONE", "82910482917"),
        ("stud-09", "Ali Reza Rostami", "2003-12-01", "MALE", "GENERAL", "AIT-2024-CSE-009", "inst-apex-1001", "CRS-CSE", True, "FOREIGN_NATIONAL", "82910482918"),

        # AI & Data Science
        ("stud-10", "Aditya Joshi", "2004-02-17", "MALE", "GENERAL", "AIT-2024-AID-001", "inst-apex-1001", "CRS-AIDS", False, "NONE", "91029384710"),
        ("stud-11", "Pooja Reddy", "2004-10-10", "FEMALE", "OBC", "AIT-2024-AID-002", "inst-apex-1001", "CRS-AIDS", False, "NONE", "91029384711"),
        ("stud-12", "Rhea Singhania", "2004-03-29", "FEMALE", "GENERAL", "AIT-2024-AID-003", "inst-apex-1001", "CRS-AIDS", True, "TFW", "91029384713"),

        # Beacon College Students
        ("stud-13", "Gautam Nair", "2004-09-02", "MALE", "GENERAL", "BEC-2024-IT-101", "inst-beacon-2002", "CRS-IT", False, "NONE", "73829104820"),
        ("stud-14", "Divya Pillai", "2004-12-14", "FEMALE", "OBC", "BEC-2024-IT-102", "inst-beacon-2002", "CRS-IT", False, "NONE", "73829104821"),
        ("stud-15", "Farhan Akhtar", "2004-05-20", "MALE", "GENERAL", "BEC-2024-IT-103", "inst-beacon-2002", "CRS-IT", True, "TFW", "73829104822")
    ]

    for sid, sname, sdob, sgen, scat, sroll, sinst, scrs, issuper, stype, base11 in synthetic_students:
        raw_ap = make_valid_apaar(base11)
        ap_hash = hash_apaar_id(raw_ap)
        ap_mask = mask_apaar_id(raw_ap)

        st_obj = Student(
            id=f"stud-uuid-{sid}",
            student_name=sname,
            date_of_birth=sdob,
            gender=sgen,
            category=scat,
            apaar_id_encrypted=raw_ap,
            apaar_hash=ap_hash,
            apaar_masked=ap_mask
        )
        db.add(st_obj)
        db.flush()

        vtoken = generate_uuid()
        sig = generate_credential_signature(vtoken, sroll, ap_hash, sinst)

        enrol_obj = StudentEnrolment(
            id=generate_uuid(),
            student_id=st_obj.id,
            internal_student_id=sroll,
            institution_id=sinst,
            course_id=scrs,
            academic_year="2024-2025",
            admission_year=2024,
            admission_category="REGULAR",
            is_supernumerary=issuper,
            supernumerary_type=stype,
            nri_status=(stype == "NRI"),
            foreign_national_status=(stype == "FOREIGN_NATIONAL"),
            admission_status="ENROLLED",
            record_status="ACCEPTED"
        )
        db.add(enrol_obj)
        db.flush()

        cred_obj = SignedCredential(
            id=generate_uuid(),
            student_id=st_obj.id,
            enrolment_id=enrol_obj.id,
            verification_token=vtoken,
            signature_algorithm="HMAC-SHA256",
            signature_value=sig
        )
        db.add(cred_obj)

        consent_obj = ConsentRecord(
            id=generate_uuid(),
            student_id=st_obj.id,
            purpose="National Academic Depository & Verification",
            status="GRANTED"
        )
        db.add(consent_obj)

    # 7. MULTIPLE ENROLMENT DISCREPANCY SCENARIO (Duplicate APAAR across institutions)
    # Student "Vikram Malhotra" has ONE student identity with APAAR, but TWO concurrent enrolments in different colleges!
    vikram_raw_ap = make_valid_apaar("66281928371")
    vikram_hash = hash_apaar_id(vikram_raw_ap)
    vikram_mask = mask_apaar_id(vikram_raw_ap)

    student_vikram = Student(
        id="stud-uuid-vikram-malhotra",
        student_name="Vikram Malhotra",
        date_of_birth="2004-06-15",
        gender="MALE",
        category="GENERAL",
        apaar_id_encrypted=vikram_raw_ap,
        apaar_hash=vikram_hash,
        apaar_masked=vikram_mask
    )
    db.add(student_vikram)
    db.flush()

    # Enrolment 1: Apex CSE
    vtok1 = generate_uuid()
    sig1 = generate_credential_signature(vtok1, "AIT-2024-CSE-099", vikram_hash, "inst-apex-1001")
    enrol_vikram_apex = StudentEnrolment(
        id=generate_uuid(),
        student_id=student_vikram.id,
        internal_student_id="AIT-2024-CSE-099",
        institution_id="inst-apex-1001",
        course_id="CRS-CSE",
        academic_year="2024-2025",
        admission_year=2024,
        admission_status="ENROLLED",
        record_status="FLAGGED_DISCREPANCY",
        discrepancy_reason="AICTE Audit Alert: Concurrent full-time enrolment detected across multiple AICTE institutions under same APAAR ID."
    )
    db.add(enrol_vikram_apex)
    db.flush()
    db.add(SignedCredential(
        id=generate_uuid(), student_id=student_vikram.id, enrolment_id=enrol_vikram_apex.id,
        verification_token=vtok1, signature_algorithm="HMAC-SHA256", signature_value=sig1
    ))

    # Enrolment 2: Beacon IT
    vtok2 = generate_uuid()
    sig2 = generate_credential_signature(vtok2, "BEC-2024-IT-199", vikram_hash, "inst-beacon-2002")
    enrol_vikram_beacon = StudentEnrolment(
        id=generate_uuid(),
        student_id=student_vikram.id,
        internal_student_id="BEC-2024-IT-199",
        institution_id="inst-beacon-2002",
        course_id="CRS-IT",
        academic_year="2024-2025",
        admission_year=2024,
        admission_status="ENROLLED",
        record_status="FLAGGED_DISCREPANCY",
        discrepancy_reason="AICTE Audit Alert: Concurrent full-time enrolment detected across multiple AICTE institutions under same APAAR ID."
    )
    db.add(enrol_vikram_beacon)
    db.flush()
    db.add(SignedCredential(
        id=generate_uuid(), student_id=student_vikram.id, enrolment_id=enrol_vikram_beacon.id,
        verification_token=vtok2, signature_algorithm="HMAC-SHA256", signature_value=sig2
    ))

    # 8. All 5 Persona Users
    users = [
        User(
            id="user-aicte-admin",
            email="admin@aicte.gov.in",
            password_hash=hash_password("Aicte@2026"),
            name="Dr. K. S. Sundaram (National Scrutiny Director)",
            role="AICTE_ADMIN",
            institution_id=None,
            is_active=True
        ),
        User(
            id="user-apex-admin",
            email="registrar@apex.edu",
            password_hash=hash_password("Apex@2026"),
            name="Prof. Sunita Deshmukh (Registrar, Apex Tech)",
            role="INSTITUTION_ADMIN",
            institution_id="inst-apex-1001",
            is_active=True
        ),
        User(
            id="user-apex-operator",
            email="operator@apex.edu",
            password_hash=hash_password("Operator@2026"),
            name="Ramesh Joshi (Data Entry Operator, Apex Tech)",
            role="INSTITUTION_OPERATOR",
            institution_id="inst-apex-1001",
            is_active=True
        ),
        User(
            id="user-student-aarav",
            email="student@apex.edu",
            password_hash=hash_password("Student@2026"),
            name="Aarav Sharma",
            role="STUDENT_VIEWER",
            institution_id="inst-apex-1001",
            student_id=student_aarav_id,
            is_active=True
        ),
        User(
            id="user-verifier-tcs",
            email="verifier@tcs.com",
            password_hash=hash_password("Tcs@2026"),
            name="Priya Varma (Lead HR Verification, Tata Consultancy Services)",
            role="AUTHORIZED_VERIFIER",
            institution_id=None,
            is_active=True
        ),
        User(
            id="user-beacon-dean",
            email="principal@beacon.ac.in",
            password_hash=hash_password("Beacon@2026"),
            name="Dr. Raghavan Nair (Dean, Beacon College)",
            role="INSTITUTION_ADMIN",
            institution_id="inst-beacon-2002",
            is_active=True
        )
    ]
    db.add_all(users)
    db.flush()

    # 9. Audit Events
    now = datetime.now(timezone.utc)
    audits = [
        AuditEvent(
            institution_id=None,
            actor_user_id="user-aicte-admin",
            actor_email="admin@aicte.gov.in",
            actor_role="AICTE_ADMIN",
            event_type="SYSTEM_INITIALIZATION",
            resource_type="CENTRAL_REGISTRY",
            resource_id="APH-2024-25",
            details_json='{"action": "AICTE Approval Process Handbook (APH) baseline quotas established.", "academic_year": "2024-2025"}',
            timestamp=now - timedelta(days=3)
        ),
        AuditEvent(
            institution_id="inst-apex-1001",
            actor_user_id="user-apex-admin",
            actor_email="registrar@apex.edu",
            actor_role="INSTITUTION_ADMIN",
            event_type="BATCH_STUDENT_ENROLMENT",
            resource_type="STUDENT_ROSTER",
            resource_id="BATCH-001",
            details_json='{"institution": "Apex Institute of Technology", "enrolled_count": 12, "status": "VERIFIED"}',
            timestamp=now - timedelta(days=2)
        ),
        AuditEvent(
            institution_id=None,
            actor_user_id="user-aicte-admin",
            actor_email="admin@aicte.gov.in",
            actor_role="AICTE_ADMIN",
            event_type="DISCREPANCY_ALERT_TRIGGERED",
            resource_type="DUPLICATE_APAAR",
            resource_id="APAAR-COLLISION-371",
            details_json='{"flag": "CONCURRENT_ENROLMENT_DISCREPANCY", "institutions": ["Apex Institute of Technology", "Beacon College of Engineering"]}',
            timestamp=now - timedelta(hours=6)
        )
    ]
    db.add_all(audits)
    db.flush()

    # 10. Seed Bulk Upload Jobs (Realistic Institutional History)
    upload_jobs = [
        BulkUploadJob(
            id="job-apex-batch-01",
            institution_id="inst-apex-1001",
            created_by_user_id="user-apex-operator",
            filename="apex_2024_btech_admissions_main.csv",
            academic_year="2024-2025",
            total_records=120,
            valid_records=118,
            error_records=2,
            status="COMPLETED",
            created_at=now - timedelta(days=5)
        ),
        BulkUploadJob(
            id="job-apex-supernumerary-02",
            institution_id="inst-apex-1001",
            created_by_user_id="user-apex-admin",
            filename="apex_supernumerary_quota_tfw_nri.csv",
            academic_year="2024-2025",
            total_records=45,
            valid_records=42,
            error_records=3,
            status="REQUIRES_RESOLUTION",
            created_at=now - timedelta(days=2)
        ),
        BulkUploadJob(
            id="job-beacon-mech-it-01",
            institution_id="inst-beacon-2002",
            created_by_user_id="user-beacon-dean",
            filename="beacon_mech_it_admissions_2024.csv",
            academic_year="2024-2025",
            total_records=85,
            valid_records=85,
            error_records=0,
            status="COMPLETED",
            created_at=now - timedelta(days=4)
        ),
        BulkUploadJob(
            id="job-beacon-lateral-02",
            institution_id="inst-beacon-2002",
            created_by_user_id="user-beacon-dean",
            filename="beacon_lateral_entry_batch2_corrupted.csv",
            academic_year="2024-2025",
            total_records=30,
            valid_records=10,
            error_records=20,
            status="FAILED",
            created_at=now - timedelta(hours=14)
        ),
        BulkUploadJob(
            id="job-zenith-cse-01",
            institution_id="inst-zenith-3003",
            created_by_user_id="user-aicte-admin",
            filename="zenith_cse_intake_roster_2024.csv",
            academic_year="2024-2025",
            total_records=180,
            valid_records=178,
            error_records=2,
            status="COMPLETED",
            created_at=now - timedelta(days=6)
        )
    ]
    db.add_all(upload_jobs)
    db.flush()

    # 11. Seed Verification Requests (Realistic Employer & Third-Party Logs)
    verifications = [
        VerificationRequest(
            id=generate_uuid(),
            token=vtok1,
            student_id=student_aarav_id,
            enrolment_id=enrol_aarav.id,
            verifier_name="Priya Varma",
            verifier_organization="Tata Consultancy Services Ltd.",
            purpose="Employment Pre-Onboarding Background Check",
            verification_result="VERIFIED",
            consent_verified=True,
            ip_address="103.25.144.12",
            created_at=now - timedelta(hours=3)
        ),
        VerificationRequest(
            id=generate_uuid(),
            token=vtok2,
            student_id=student_vikram.id,
            enrolment_id=enrol_vikram_apex.id,
            verifier_name="Rajesh Sen",
            verifier_organization="Infosys Campus Verification Directorate",
            purpose="Campus Placement Credential Validation",
            verification_result="VERIFIED",
            consent_verified=True,
            ip_address="49.207.180.45",
            created_at=now - timedelta(hours=18)
        ),
        VerificationRequest(
            id=generate_uuid(),
            token="invalid-tampered-token-99812",
            student_id=None,
            enrolment_id=None,
            verifier_name="External Auditor",
            verifier_organization="State Technical Education Board",
            purpose="Annual Registry Audit",
            verification_result="NOT_FOUND",
            consent_verified=False,
            ip_address="122.161.49.88",
            created_at=now - timedelta(days=1)
        )
    ]
    db.add_all(verifications)
    db.commit()

    # 12. Run initial Validation Audit to persist deterministic statutory issues
    try:
        engine = ValidationEngine()
        institutions = db.query(Institution).all()
        now = datetime.now(timezone.utc)
        for inst in institutions:
            issues = engine.audit_institution(db, inst.id, academic_year="2024-2025")
            for iss in issues:
                raw_json = json.dumps(iss.metadata) if hasattr(iss, "metadata") and iss.metadata else None
                db.add(ValidationIssue(
                    institution_id=inst.id,
                    enrolment_id=iss.entity_id,
                    rule_id=iss.rule_id,
                    field_name=iss.field_name,
                    error_code=iss.error_code,
                    error_message=iss.error_message,
                    suggested_remediation=iss.suggested_remediation,
                    severity=iss.severity,
                    anomaly_score=iss.anomaly_score,
                    raw_data_json=raw_json,
                    resolution_status="NEW",
                    created_at=now,
                    updated_at=now
                ))
        db.commit()
    except Exception as e:
        print(f"Initial validation audit warning: {e}")

if __name__ == "__main__":
    from .session import SessionLocal, engine, Base
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_database(db, force_reset=True)
    db.close()
    print("Persistent Database successfully initialized and seeded with synthetic data.")
