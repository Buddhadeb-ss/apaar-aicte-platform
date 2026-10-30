import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.identifiers import (
    validate_apaar_format,
    calculate_verhoeff_checksum,
    mask_apaar_id,
    hash_apaar_id,
    normalize_identifier
)

from app.database.session import SessionLocal, Base, engine
from app.database.seed_data import seed_database

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_database(db, force_reset=True)
    db.close()
    with TestClient(app) as c:
        yield c

# ----------------- 1. HEALTH & READINESS PROBE -----------------

def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["problem_statement"] == "SIH26263"
    assert data["database_connected"] is True
    assert data["persistent_records"]["institutions_loaded"] >= 3
    assert data["persistent_records"]["enrolments_loaded"] >= 15
    assert data["simulated_gateway"] is True

# ----------------- 2. AUTHENTICATION & ALL 5 ROLES -----------------

def test_all_5_demo_personas_and_permissions(client):
    # Check demo profiles list
    res = client.get("/api/v1/auth/demo-profiles")
    assert res.status_code == 200
    profiles = res.json()
    assert len(profiles) >= 5
    roles = [p["role"] for p in profiles]
    assert "AICTE_ADMIN" in roles
    assert "INSTITUTION_ADMIN" in roles
    assert "INSTITUTION_OPERATOR" in roles
    assert "STUDENT_VIEWER" in roles
    assert "AUTHORIZED_VERIFIER" in roles

    # 1. Login AICTE Admin (Index 0)
    res_aicte = client.post("/api/v1/auth/demo-login/0")
    assert res_aicte.status_code == 200
    token_aicte = res_aicte.json()["access_token"]
    me_aicte = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_aicte}"}).json()
    assert me_aicte["role"] == "AICTE_ADMIN"

    # 2. Login Institution Admin (Index 1 - Apex)
    res_inst = client.post("/api/v1/auth/demo-login/1")
    assert res_inst.status_code == 200
    token_inst = res_inst.json()["access_token"]
    me_inst = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_inst}"}).json()
    assert me_inst["role"] == "INSTITUTION_ADMIN"
    assert me_inst["institution_id"] == "inst-apex-1001"

    # 3. Login Institution Operator (Index 2 - Apex)
    res_op = client.post("/api/v1/auth/demo-login/2")
    assert res_op.status_code == 200
    token_op = res_op.json()["access_token"]
    me_op = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_op}"}).json()
    assert me_op["role"] == "INSTITUTION_OPERATOR"

    # 4. Login Student Viewer (Index 3 - Aarav)
    res_stud = client.post("/api/v1/auth/demo-login/3")
    assert res_stud.status_code == 200
    token_stud = res_stud.json()["access_token"]
    me_stud = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_stud}"}).json()
    assert me_stud["role"] == "STUDENT_VIEWER"

    # 5. Login Authorized Verifier (Index 4 - TCS HR)
    res_verif = client.post("/api/v1/auth/demo-login/4")
    assert res_verif.status_code == 200
    token_verif = res_verif.json()["access_token"]
    me_verif = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_verif}"}).json()
    assert me_verif["role"] == "AUTHORIZED_VERIFIER"

# ----------------- 3. TENANT ISOLATION & PERMISSIONS -----------------

def test_tenant_isolation_and_scoping(client):
    # Login as Apex Registrar
    res_apex = client.post("/api/v1/auth/demo-login/1")
    token_apex = res_apex.json()["access_token"]
    headers_apex = {"Authorization": f"Bearer {token_apex}"}

    # Apex Admin cannot inspect Beacon College (inst-beacon-2002)
    forbidden_res = client.get("/api/v1/institutions/inst-beacon-2002", headers=headers_apex)
    assert forbidden_res.status_code == 403

    # Verifier cannot create students
    res_verif = client.post("/api/v1/auth/demo-login/4")
    token_verif = res_verif.json()["access_token"]
    headers_verif = {"Authorization": f"Bearer {token_verif}"}

    sample_student = {
        "student_name": "Test Student",
        "date_of_birth": "2004-01-01",
        "gender": "MALE",
        "category": "GENERAL",
        "internal_student_id": "TEST-001",
        "course_id": "CRS-CSE",
        "academic_year": "2024-2025",
        "admission_year": 2024,
        "apaar_id": "829104829202"
    }
    create_res = client.post("/api/v1/students", json=sample_student, headers=headers_verif)
    assert create_res.status_code == 403

# ----------------- 4. STUDENT CRUD & APAAR PRIVACY -----------------

def test_student_crud_and_privacy_masking(client):
    # Login as Apex Registrar
    res_apex = client.post("/api/v1/auth/demo-login/1")
    token_apex = res_apex.json()["access_token"]
    headers_apex = {"Authorization": f"Bearer {token_apex}"}

    # Valid 12-digit APAAR with Verhoeff
    base = "82910482944"
    c = calculate_verhoeff_checksum(base)
    valid_apaar = f"{base}{c}"

    new_student_payload = {
        "student_name": "Tarun Singhal",
        "date_of_birth": "2004-08-19",
        "gender": "MALE",
        "category": "OBC",
        "internal_student_id": "AIT-2024-CSE-555",
        "course_id": "CRS-CSE",
        "academic_year": "2024-2025",
        "admission_year": 2024,
        "apaar_id": valid_apaar,
        "is_supernumerary": False,
        "supernumerary_type": "NONE"
    }

    # 1. Create Student Enrolment
    create_res = client.post("/api/v1/students", json=new_student_payload, headers=headers_apex)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["internal_student_id"] == "AIT-2024-CSE-555"
    assert created_data["student_name"] == "Tarun Singhal"
    # PRIVACY RULE: APAAR ID must NEVER be exposed in clear text
    assert created_data["apaar_masked"] == f"•••• •••• {valid_apaar[-4:]}"
    assert valid_apaar not in str(created_data)

    # 2. Test duplicate internal roll number rejection in same institution & session
    dup_res = client.post("/api/v1/students", json=new_student_payload, headers=headers_apex)
    assert dup_res.status_code == 400
    assert "already registered" in dup_res.json()["detail"]

    # 3. Retrieve student in paginated list
    list_res = client.get("/api/v1/students?search=Tarun", headers=headers_apex)
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert len(items) >= 1
    assert items[0]["internal_student_id"] == "AIT-2024-CSE-555"
    assert items[0]["apaar_masked"].startswith("•••• •••• ")

# ----------------- 5. INTAKE RECONCILIATION & DUPLICATE COLLISION -----------------

def test_intake_reconciliation_schedule(client):
    res_apex = client.post("/api/v1/auth/demo-login/1")
    token_apex = res_apex.json()["access_token"]
    headers_apex = {"Authorization": f"Bearer {token_apex}"}

    rec_res = client.get("/api/v1/intakes/reconciliation/inst-apex-1001", headers=headers_apex)
    assert rec_res.status_code == 200
    data = rec_res.json()
    assert data["institution_id"] == "inst-apex-1001"
    rows = data["reconciliation_rows"]
    assert len(rows) >= 3

    cse_row = next(r for r in rows if "Computer Science" in r["course"])
    assert cse_row["approved_intake"] == 120
    assert cse_row["regular_enrolled"] > 0
    assert cse_row["variance"] == 120 - cse_row["regular_enrolled"]

def test_duplicate_apaar_collision_detection(client):
    # Login as AICTE Admin
    res_aicte = client.post("/api/v1/auth/demo-login/0")
    token_aicte = res_aicte.json()["access_token"]
    headers_aicte = {"Authorization": f"Bearer {token_aicte}"}

    # Query collision alerts
    dup_res = client.get("/api/v1/dashboard/duplicates", headers=headers_aicte)
    assert dup_res.status_code == 200
    dups = dup_res.json()
    assert len(dups) >= 1
    # Vikram Malhotra is enrolled concurrently at Apex and Beacon
    vikram = next(d for d in dups if "Vikram" in d["student_name"])
    assert len(vikram["enrolments"]) >= 2
    inst_names = {e["institution_name"] for e in vikram["enrolments"]}
    assert "Apex Institute of Technology" in inst_names
    assert "Beacon College of Engineering" in inst_names

# ----------------- 6. BULK UPLOADS & VALIDATION ISSUES RESOLUTION -----------------

def test_bulk_upload_job_and_inline_resolution(client):
    res_apex = client.post("/api/v1/auth/demo-login/1")
    token_apex = res_apex.json()["access_token"]
    headers_apex = {"Authorization": f"Bearer {token_apex}"}

    # CSV with 1 valid row and 1 invalid row (malformed APAAR)
    valid_base = "82910482977"
    valid_c = calculate_verhoeff_checksum(valid_base)
    valid_ap = f"{valid_base}{valid_c}"

    csv_content = f"""internal_id,student_name,date_of_birth,gender,category,course,apaar_id,is_supernumerary,supernumerary_type
AIT-2024-CSE-901,Priya Sharma,2004-03-21,FEMALE,GENERAL,Computer Science & Engineering,{valid_ap},FALSE,NONE
AIT-2024-CSE-902,Suresh Kumar,2004-09-15,MALE,OBC,Computer Science & Engineering,999999999999,FALSE,NONE
"""

    file_obj = io.BytesIO(csv_content.encode('utf-8'))
    files = {"file": ("students_batch.csv", file_obj, "text/csv")}
    data = {"academic_year": "2024-2025"}

    # 1. Upload CSV
    upload_res = client.post("/api/v1/upload-jobs", files=files, data=data, headers=headers_apex)
    assert upload_res.status_code == 201
    job_data = upload_res.json()
    assert job_data["total_records"] == 2
    assert job_data["valid_records"] == 1
    assert job_data["error_records"] == 1
    assert job_data["status"] == "REQUIRES_RESOLUTION"

    # 2. Inspect validation issues
    issues_res = client.get(f"/api/v1/validation/issues/{job_data['id']}", headers=headers_apex)
    assert issues_res.status_code == 200
    issues = issues_res.json()
    assert len(issues) == 1
    assert issues[0]["row_number"] == 2
    assert issues[0]["error_code"] == "INVALID_APAAR_FORMAT"

    # 3. Resolve the issue with corrected APAAR
    corrected_base = "82910482988"
    corrected_c = calculate_verhoeff_checksum(corrected_base)
    corrected_ap = f"{corrected_base}{corrected_c}"

    resolve_payload = {
        "job_id": job_data["id"],
        "resolved_rows": [
            {
                "issue_id": issues[0]["id"],
                "internal_student_id": "AIT-2024-CSE-902",
                "student_name": "Suresh Kumar",
                "apaar_id": corrected_ap,
                "course_id": "CRS-CSE",
                "date_of_birth": "2004-09-15",
                "category": "OBC",
                "supernumerary_type": "NONE"
            }
        ]
    }
    resolve_res = client.post("/api/v1/validation/resolve", json=resolve_payload, headers=headers_apex)
    assert resolve_res.status_code == 200
    rdata = resolve_res.json()
    assert rdata["resolved_count"] == 1
    assert rdata["remaining_error_count"] == 0
    assert rdata["job_status"] == "COMPLETED"

# ----------------- 7. VERIFICATION & CONSENT -----------------

def test_credential_verification_with_signature_and_consent(client):
    # 1. Student Aarav requests his credential
    res_stud = client.post("/api/v1/auth/demo-login/3")
    token_stud = res_stud.json()["access_token"]
    headers_stud = {"Authorization": f"Bearer {token_stud}"}

    cred_res = client.get("/api/v1/students/stud-uuid-aarav-sharma-2024/credential", headers=headers_stud)
    assert cred_res.status_code == 200
    cred = cred_res.json()
    assert cred["qr_code_base64"].startswith("data:image/png;base64,")
    assert cred["credential_signature"].startswith("SIG_v1_")
    assert cred["consent_status"] == "GRANTED"

    # 2. Third-Party Verifier tests token
    verif_payload = {
        "token": cred["verification_token"],
        "verifier_name": "Priya Varma",
        "verifier_organization": "Tata Consultancy Services (TCS)",
        "purpose": "Pre-Employment Background Verification"
    }
    verify_res = client.post("/api/v1/verifications/verify", json=verif_payload)
    assert verify_res.status_code == 200
    vdata = verify_res.json()
    assert vdata["status"] == "VERIFIED"
    assert vdata["is_valid"] is True
    assert vdata["signature_verified"] is True
    assert vdata["consent_verified"] is True
    assert vdata["student_name"] == "Aarav Sharma"
    assert vdata["apaar_masked"].startswith("•••• •••• ")

    # 3. Test tampered token
    tampered_payload = {
        "token": "fake-tampered-token-12345",
        "verifier_name": "Unknown",
        "verifier_organization": "Audit Inc",
        "purpose": "Penetration Testing"
    }
    tampered_res = client.post("/api/v1/verifications/verify", json=tampered_payload)
    assert tampered_res.status_code == 200
    tdata = tampered_res.json()
    assert tdata["status"] == "NOT_FOUND"
    assert tdata["is_valid"] is False

# ----------------- 8. STATUTORY REPORTS & PDF -----------------

def test_reports_and_pdf_generation(client):
    res_apex = client.post("/api/v1/auth/demo-login/1")
    token_apex = res_apex.json()["access_token"]
    headers_apex = {"Authorization": f"Bearer {token_apex}"}

    # Intake Compliance PDF
    pdf_res = client.get("/api/v1/reports/intake-compliance-pdf/inst-apex-1001", headers=headers_apex)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000

    # Audit Events Trail
    audit_res = client.get("/api/v1/reports/audit-events", headers=headers_apex)
    assert audit_res.status_code == 200
    events = audit_res.json()
    assert len(events) >= 1

# ----------------- 9. STUDENT DETAIL, EDIT & AUDIT HISTORY -----------------

def test_student_detail_update_and_history(client):
    res_apex = client.post("/api/v1/auth/demo-login/1")
    token_apex = res_apex.json()["access_token"]
    headers_apex = {"Authorization": f"Bearer {token_apex}"}

    # 1. Fetch Aarav Sharma's details
    aarav_res = client.get("/api/v1/students/enrol-uuid-aarav-apex-cse", headers=headers_apex)
    assert aarav_res.status_code == 200
    aarav = aarav_res.json()
    assert aarav["student_name"] == "Aarav Sharma"
    assert aarav["course_id"] == "CRS-CSE"

    # 2. Update Aarav's name and category
    update_payload = {
        "student_name": "Aarav K. Sharma",
        "date_of_birth": "2004-03-15",
        "gender": "MALE",
        "category": "EWS",
        "internal_student_id": "AIT-2024-CSE-007",
        "course_id": "CRS-CSE",
        "academic_year": "2024-2025",
        "admission_year": 2024,
        "admission_status": "ADMITTED",
        "is_supernumerary": False,
        "supernumerary_type": "NONE",
        "nri_status": False,
        "oci_status": False,
        "foreign_national_status": False
    }
    update_res = client.put("/api/v1/students/enrol-uuid-aarav-apex-cse", json=update_payload, headers=headers_apex)
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["student_name"] == "Aarav K. Sharma"
    assert updated["category"] == "EWS"
    assert updated["admission_status"] == "ADMITTED"

    # 3. Check Audit Change History
    hist_res = client.get("/api/v1/students/enrol-uuid-aarav-apex-cse/history", headers=headers_apex)
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 1
    assert any(h["event_type"] == "STUDENT_UPDATED" for h in history)

# ----------------- 10. BULK WIZARD DRY-RUN & COMMIT -----------------

def test_bulk_wizard_workflow(client):
    res_apex = client.post("/api/v1/auth/demo-login/1")
    token_apex = res_apex.json()["access_token"]
    headers_apex = {"Authorization": f"Bearer {token_apex}"}

    # 1. Download template
    tmpl_res = client.get("/api/v1/upload-jobs/template")
    assert tmpl_res.status_code == 200
    assert "internal_id,student_name" in tmpl_res.text

    # 2. Pre-Validation Dry Run with 1 valid and 1 invalid row
    dry_run_payload = {
        "institution_id": "inst-apex-1001",
        "academic_year": "2024-2025",
        "rows": [
            {
                "internal_id": "WIZ-TEST-001",
                "student_name": "Valid Wizard Student",
                "date_of_birth": "2004-05-10",
                "course": "CRS-CSE",
                "apaar_id": "829104829204"
            },
            {
                "internal_id": "",
                "student_name": "Invalid Row Missing Roll",
                "date_of_birth": "2004-05-10",
                "course": "CRS-CSE",
                "apaar_id": "111111111111"
            }
        ]
    }
    dry_res = client.post("/api/v1/upload-jobs/validate", json=dry_run_payload, headers=headers_apex)
    assert dry_res.status_code == 200
    dry_data = dry_res.json()
    assert dry_data["total_rows"] == 2
    assert dry_data["valid_rows_count"] == 1
    assert dry_data["invalid_rows_count"] == 1
    assert dry_data["can_commit"] is True

    # 3. Explicit Confirmation Commit
    commit_payload = {
        "filename": "wizard_batch.csv",
        "academic_year": "2024-2025",
        "institution_id": "inst-apex-1001",
        "rows": dry_run_payload["rows"]
    }
    commit_res = client.post("/api/v1/upload-jobs/commit", json=commit_payload, headers=headers_apex)
    assert commit_res.status_code == 200
    summary = commit_res.json()
    assert summary["accepted_count"] == 1
    assert summary["rejected_count"] == 1
    assert summary["status"] == "REQUIRES_RESOLUTION"

    # 4. Export Errors CSV
    err_res = client.get(f"/api/v1/upload-jobs/{summary['job_id']}/export-errors", headers=headers_apex)
    assert err_res.status_code == 200
    assert "Row Number,Field Name,Error Code" in err_res.text
