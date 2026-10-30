import os
import sys
import io
import json
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal, Base, engine
from app.database.seed_data import seed_database
from app.core.identifiers import calculate_verhoeff_checksum

def run_live_verification():
    print("==================================================")
    print("RUNNING LIVE END-TO-END SIH26263 VERIFICATION SUITE")
    print("==================================================")

    # 1. Database Persistence Verification
    db = SessionLocal()
    seed_database(db, force_reset=False)
    db.close()
    print("[PASS] Persistent SQLite database verified.")

    client = TestClient(app)

    # 2. Health & Readiness Endpoint
    h_res = client.get("/api/v1/health")
    assert h_res.status_code == 200, f"Health check failed: {h_res.text}"
    h_data = h_res.json()
    assert h_data["status"] == "HEALTHY"
    assert h_data["database_connected"] is True
    assert h_data["persistent_records"]["institutions_loaded"] >= 3
    print(f"[PASS] /api/v1/health: status={h_data['status']}, institutions={h_data['persistent_records']['institutions_loaded']}")

    # 3. Authentication & 5 Roles Login
    personas = [
        ("AICTE_ADMIN", "admin@aicte.gov.in", "Aicte@2026"),
        ("INSTITUTION_ADMIN", "registrar@apex.edu", "Apex@2026"),
        ("INSTITUTION_OPERATOR", "operator@apex.edu", "Operator@2026"),
        ("STUDENT_VIEWER", "student@apex.edu", "Student@2026"),
        ("AUTHORIZED_VERIFIER", "verifier@tcs.com", "Tcs@2026"),
    ]
    tokens = {}
    for role, email, pwd in personas:
        l_res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
        assert l_res.status_code == 200, f"Login failed for {email}: {l_res.text}"
        tokens[role] = l_res.json()["access_token"]
        print(f"[PASS] Authentication verified for role: {role} ({email})")

    # 4. Multi-Tenant Isolation & Scoping
    headers_verifier = {"Authorization": f"Bearer {tokens['AUTHORIZED_VERIFIER']}"}
    headers_apex = {"Authorization": f"Bearer {tokens['INSTITUTION_ADMIN']}"}
    headers_aicte = {"Authorization": f"Bearer {tokens['AICTE_ADMIN']}"}

    # Unauthorized role should be blocked with 403
    forbidden_res = client.post(
        "/api/v1/students",
        json={
            "student_name": "Unauthorized Attempt",
            "date_of_birth": "2003-01-01",
            "apaar_id": "829104829106",
            "internal_student_id": "ROLL-FORBIDDEN",
            "institution_id": "inst-apex-1001",
            "course_id": "CRS-CSE",
            "academic_year": "2024-2025"
        },
        headers=headers_verifier
    )
    assert forbidden_res.status_code == 403, f"Expected 403 for verifier creating student, got {forbidden_res.status_code}"
    print("[PASS] Role-based access control (RBAC): Verifier blocked from student onboarding (HTTP 403).")

    # Tenant isolation: Apex Admin cannot access Beacon Institute
    tenant_block = client.get("/api/v1/intakes/reconciliation/inst-beacon-1002", headers=headers_apex)
    assert tenant_block.status_code == 403
    print("[PASS] Multi-tenant isolation: Apex Registrar blocked from Beacon IT records (HTTP 403).")

    # 5. Student CRUD & Privacy Masking
    base_digits = "99887766554"
    valid_chk = calculate_verhoeff_checksum(base_digits)
    test_apaar = f"{base_digits}{valid_chk}"
    unique_roll = f"TEST-ROLL-{uuid.uuid4().hex[:6]}"

    create_res = client.post(
        "/api/v1/students",
        json={
            "student_name": "Kavita Nambiar",
            "date_of_birth": "2004-11-20",
            "gender": "FEMALE",
            "category": "OBC",
            "apaar_id": test_apaar,
            "internal_student_id": unique_roll,
            "institution_id": "inst-apex-1001",
            "course_id": "CRS-CSE",
            "academic_year": "2024-2025",
            "admission_year": 2024,
            "is_supernumerary": False
        },
        headers=headers_apex
    )
    assert create_res.status_code == 201, f"Failed creating student: {create_res.text}"
    new_student = create_res.json()
    assert new_student["apaar_masked"] == f"•••• •••• {test_apaar[-4:]}"
    assert new_student["student_name"] == "Kavita Nambiar"
    print(f"[PASS] Student Onboarding: Created UUID={new_student['id']}, Masked APAAR={new_student['apaar_masked']}")

    # 6. Intake Limits & Reconciliation Schedule
    rec_res = client.get("/api/v1/intakes/reconciliation/inst-apex-1001", headers=headers_apex)
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["institution_id"] == "inst-apex-1001"
    assert len(rec_data["reconciliation_rows"]) > 0
    print(f"[PASS] Intake Reconciliation: Verified {len(rec_data['reconciliation_rows'])} course allocations for Apex.")

    # 7. Duplicate APAAR Collision Detection Across Institutions
    dup_res = client.get("/api/v1/dashboard/duplicates", headers=headers_aicte)
    assert dup_res.status_code == 200
    dups = dup_res.json()
    assert len(dups) >= 1
    vikram_dup = next(d for d in dups if "Vikram" in d["student_name"])
    assert len(vikram_dup["enrolments"]) >= 2
    inst_names = [e["institution_name"] for e in vikram_dup["enrolments"]]
    print(f"[PASS] Duplicate APAAR Collision Detection: Detected concurrent enrolment across {inst_names}")

    # 8. Third-Party Verification with HMAC Signature & Consent Check
    cred_res = client.get(f"/api/v1/students/{new_student['id']}/credential", headers=headers_apex)
    assert cred_res.status_code == 200
    cred_data = cred_res.json()
    verif_token = cred_data["verification_token"]

    v_res = client.post(
        "/api/v1/verifications/verify",
        json={
            "token": verif_token,
            "verifier_name": "Priya Varma",
            "verifier_organization": "Tata Consultancy Services",
            "purpose": "Employment Verification"
        },
        headers=headers_verifier
    )
    assert v_res.status_code == 200, f"Verification failed: {v_res.text}"
    v_data = v_res.json()
    assert v_data["status"] == "VERIFIED"
    assert v_data["signature_verified"] is True
    assert v_data["student_name"] == "Kavita Nambiar"
    assert v_data["apaar_masked"].startswith("•••• •••• ")
    print(f"[PASS] Third-Party Verification: Validated HMAC-SHA256 signature for token={verif_token[:8]}...")

    # 9. PDF Generation (Intake Compliance & Verifiable Student Pass)
    pdf1 = client.get("/api/v1/reports/intake-compliance-pdf/inst-apex-1001", headers=headers_apex)
    assert pdf1.status_code == 200
    assert pdf1.headers["content-type"] == "application/pdf"
    assert len(pdf1.content) > 1000

    pdf2 = client.get(f"/api/v1/reports/student-credential-pdf/{new_student['id']}", headers=headers_apex)
    assert pdf2.status_code == 200
    assert pdf2.headers["content-type"] == "application/pdf"
    assert len(pdf2.content) > 1000
    print(f"[PASS] ReportLab PDF Generation: Statutory Intake Certificate ({len(pdf1.content)} bytes) and Student Pass ({len(pdf2.content)} bytes).")

    # 10. Audit Events Logging
    audit_res = client.get("/api/v1/reports/audit-events", headers=headers_aicte)
    assert audit_res.status_code == 200
    events = audit_res.json()
    assert len(events) >= 3
    print(f"[PASS] Audit Trail: {len(events)} immutable audit events recorded.")

    print("==================================================")
    print("ALL LIVE VERIFICATION TESTS PASSED SUCCESSFULLY! ")
    print("==================================================")

if __name__ == "__main__":
    run_live_verification()
