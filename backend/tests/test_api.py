import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.apaar_validator import (
    validate_apaar_format,
    calculate_verhoeff_checksum,
    mask_apaar_id,
    hash_apaar_id
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

def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["problem_statement"] == "SIH26263"
    assert data["database_connected"] is True
    assert data["simulated_gateway"] is True

def test_apaar_validator_logic():
    # Valid 11 digits + Verhoeff digit
    base = "82910482910"
    checksum = calculate_verhoeff_checksum(base)
    full_apaar = f"{base}{checksum}"
    
    is_valid, cleaned, err = validate_apaar_format(full_apaar)
    assert is_valid is True
    assert cleaned == full_apaar
    assert err is None

    # Invalid length
    is_valid, _, err = validate_apaar_format("12345")
    assert is_valid is False
    assert "12 digits" in err

    # Repetitive digits
    is_valid, _, err = validate_apaar_format("111111111111")
    assert is_valid is False
    assert "identical digits" in err

    # Masking test: never reveals first 8 digits
    masked = mask_apaar_id(full_apaar)
    assert masked.startswith("•••• •••• ")
    assert masked.endswith(full_apaar[-4:])

def test_demo_profiles(client):
    response = client.get("/api/auth/demo-profiles")
    assert response.status_code == 200
    profiles = response.json()
    assert len(profiles) >= 4
    roles = {p["role"] for p in profiles}
    assert "AICTE_ADMIN" in roles
    assert "INSTITUTE_ADMIN" in roles
    assert "STUDENT" in roles
    assert "VERIFIER" in roles

def test_demo_login_and_aicte_analytics(client):
    # 1. Login as AICTE Admin
    login_res = client.post("/api/auth/demo-login/0")
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Query National Analytics
    analytics_res = client.get("/api/aicte/analytics", headers=headers)
    assert analytics_res.status_code == 200
    data = analytics_res.json()
    assert data["total_institutions"] >= 2
    assert data["total_approved_intake"] > 0
    assert data["total_actual_enrolled"] > 0
    assert data["duplicate_apaar_violations"] >= 1  # Duplicate detection working!

def test_duplicate_apaar_detection(client):
    login_res = client.post("/api/auth/demo-login/0")
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    dup_res = client.get("/api/aicte/duplicates", headers=headers)
    assert dup_res.status_code == 200
    dups = dup_res.json()
    assert len(dups) >= 1
    dup_item = dups[0]
    assert len(dup_item["institutions_involved"]) >= 2
    assert "Vikram Malhotra" in dup_item["student_name"]

def test_institution_intake_reconciliation(client):
    # Login as Apex Registrar
    login_res = client.post("/api/auth/demo-login/1")
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    rec_res = client.get("/api/institutions/inst-apex-1001/reconciliation", headers=headers)
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["institution_id"] == "inst-apex-1001"
    assert len(rec_data["reconciliation_rows"]) >= 1

    # Check course separation
    cse_row = next(r for r in rec_data["reconciliation_rows"] if "Computer Science" in r["course"])
    assert cse_row["approved_intake"] == 120
    assert cse_row["regular_enrolled"] > 0

def test_student_credential_and_qr_verification(client):
    # 1. Login as Student
    login_res = client.post("/api/auth/demo-login/3")
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Student's list to find Aarav's ID
    students_res = client.get("/api/students", headers=headers)
    assert students_res.status_code == 200
    students = students_res.json()
    aarav = next(s for s in students if "Aarav" in s["student_name"])

    # 3. Get Aarav's Credential Card
    cred_res = client.get(f"/api/students/{aarav['id']}/credential", headers=headers)
    assert cred_res.status_code == 200
    cred = cred_res.json()
    assert cred["qr_code_base64"].startswith("data:image/png;base64,")
    assert cred["credential_signature"].startswith("SIG_v1_")

    # 4. Third-Party Verifier checks the token
    verif_payload = {
        "token": cred["verification_token"],
        "verifier_name": "Priya Varma",
        "verifier_organization": "Tata Consultancy Services",
        "purpose": "Employment Background Verification"
    }
    verify_res = client.post("/api/verification/verify-qr", json=verif_payload)
    assert verify_res.status_code == 200
    vdata = verify_res.json()
    assert vdata["status"] == "VERIFIED"
    assert vdata["signature_verified"] is True
    assert vdata["student_name"] == "Aarav Sharma"
    assert vdata["apaar_masked"].startswith("•••• •••• ")

def test_csv_template_download(client):
    res = client.get("/api/import/template")
    assert res.status_code == 200
    assert "internal_id,student_name" in res.text

def test_pdf_compliance_report(client):
    login_res = client.post("/api/auth/demo-login/0")
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    pdf_res = client.get("/api/reports/institution-intake-pdf/inst-apex-1001", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000  # Valid PDF binary generated
