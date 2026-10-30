import pytest
from fastapi.testclient import TestClient

def test_acceptance_manual_create_and_edit_student(client: TestClient):
    """
    ACCEPTANCE TEST 1:
    - Create a student manually with required and optional fields.
    - Check non-mutually exclusive nationality categories (NRI + OCI).
    - Edit the student and verify update is persisted in database.
    - Verify change history is recorded in statutory audit events.
    """
    # Login as Apex Registrar
    login_res = client.post("/api/v1/auth/demo-login/1")
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create student
    create_payload = {
        "student_name": "Aadi Narayan",
        "date_of_birth": "2004-06-20",
        "gender": "MALE",
        "category": "GENERAL",
        "internal_student_id": "AIT-2024-CSE-ACCEPT-01",
        "course_id": "CRS-CSE",
        "academic_year": "2024-2025",
        "admission_year": 2024,
        "apaar_id": "829104829204",  # Valid Verhoeff checksum
        "is_supernumerary": True,
        "supernumerary_type": "NRI",
        "nri_status": True,
        "oci_status": True,
        "foreign_national_status": False
    }

    create_res = client.post("/api/v1/students", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    created_student = create_res.json()
    student_enrol_id = created_student["id"]
    assert created_student["student_name"] == "Aadi Narayan"
    assert created_student["internal_student_id"] == "AIT-2024-CSE-ACCEPT-01"
    assert created_student["apaar_masked"] == "•••• •••• 9204"
    assert created_student["nri_status"] is True
    assert created_student["oci_status"] is True

    # 2. Edit student
    edit_payload = {
        "student_name": "Aadi V. Narayan",
        "date_of_birth": "2004-06-20",
        "gender": "MALE",
        "category": "OBC",
        "internal_student_id": "AIT-2024-CSE-ACCEPT-01",
        "course_id": "CRS-CSE",
        "academic_year": "2024-2025",
        "admission_year": 2024,
        "admission_status": "ENROLLED",
        "is_supernumerary": True,
        "supernumerary_type": "NRI",
        "nri_status": True,
        "oci_status": True,
        "foreign_national_status": True  # All nationality flags simultaneously valid
    }

    edit_res = client.put(f"/api/v1/students/{student_enrol_id}", json=edit_payload, headers=headers)
    assert edit_res.status_code == 200
    edited = edit_res.json()
    assert edited["student_name"] == "Aadi V. Narayan"
    assert edited["category"] == "OBC"
    assert edited["foreign_national_status"] is True

    # 3. Refresh / retrieve to verify persistence
    get_res = client.get(f"/api/v1/students/{student_enrol_id}", headers=headers)
    assert get_res.status_code == 200
    persisted = get_res.json()
    assert persisted["student_name"] == "Aadi V. Narayan"
    assert persisted["category"] == "OBC"

    # 4. Verify Change History Audit Trail
    hist_res = client.get(f"/api/v1/students/{student_enrol_id}/history", headers=headers)
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 1
    assert any(h["event_type"] == "STUDENT_UPDATED" for h in history)

def test_acceptance_bulk_csv_wizard_validation_and_confirmation(client: TestClient):
    """
    ACCEPTANCE TEST 2:
    - Pre-validate bulk data via dry run.
    - Check row-level failure reporting for invalid CSV data.
    - Download/export error report.
    - Confirm commit of valid records.
    - Verify persisted records in Central Registry.
    """
    login_res = client.post("/api/v1/auth/demo-login/1")
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Download official CSV template
    template_res = client.get("/api/v1/upload-jobs/template")
    assert template_res.status_code == 200
    assert "internal_id,student_name,date_of_birth" in template_res.text

    # 2. Dry run with mixed valid and invalid rows
    dry_run_payload = {
        "institution_id": "inst-apex-1001",
        "academic_year": "2024-2025",
        "rows": [
            {
                "internal_id": "ACC-BULK-VALID-01",
                "student_name": "Sanya Malhotra",
                "date_of_birth": "2004-09-12",
                "course": "CRS-CSE",
                "apaar_id": "829104829301"  # Unique valid Verhoeff APAAR
            },
            {
                "internal_id": "",  # Missing required field
                "student_name": "Incomplete Student",
                "date_of_birth": "2004-01-01",
                "course": "CRS-CSE",
                "apaar_id": "829104829301"
            },
            {
                "internal_id": "ACC-BULK-INV-02",
                "student_name": "Invalid APAAR Student",
                "date_of_birth": "2004-02-02",
                "course": "CRS-CSE",
                "apaar_id": "123456789012"  # Invalid Verhoeff checksum
            }
        ]
    }

    dry_res = client.post("/api/v1/upload-jobs/validate", json=dry_run_payload, headers=headers)
    assert dry_res.status_code == 200
    dry_data = dry_res.json()
    assert dry_data["total_rows"] == 3
    assert dry_data["valid_rows_count"] == 1
    assert dry_data["invalid_rows_count"] == 2
    assert len(dry_data["errors"]) >= 2
    assert dry_data["can_commit"] is True

    # 3. Explicit Confirmation Commit
    commit_payload = {
        "filename": "acceptance_batch.csv",
        "academic_year": "2024-2025",
        "institution_id": "inst-apex-1001",
        "rows": dry_run_payload["rows"]
    }

    commit_res = client.post("/api/v1/upload-jobs/commit", json=commit_payload, headers=headers)
    assert commit_res.status_code == 200
    summary = commit_res.json()
    assert summary["accepted_count"] == 1
    assert summary["rejected_count"] == 2
    assert summary["status"] == "REQUIRES_RESOLUTION"

    # 4. Download Error Report
    job_id = summary["job_id"]
    err_csv_res = client.get(f"/api/v1/upload-jobs/{job_id}/export-errors", headers=headers)
    assert err_csv_res.status_code == 200
    assert "Row Number,Field Name,Error Code" in err_csv_res.text

    # 5. Verify valid record persists in Central Registry
    students_res = client.get("/api/v1/students?search=ACC-BULK-VALID-01", headers=headers)
    assert students_res.status_code == 200
    found_students = students_res.json()["items"]
    assert len(found_students) == 1
    assert found_students[0]["student_name"] == "Sanya Malhotra"

def test_acceptance_strict_tenant_isolation(client: TestClient):
    """
    ACCEPTANCE TEST 3:
    - Verify that an institution user cannot access another institution's records
      by changing a URL or API request parameter.
    """
    # Login as Apex Registrar
    res_apex = client.post("/api/v1/auth/demo-login/1")
    token_apex = res_apex.json()["access_token"]
    headers_apex = {"Authorization": f"Bearer {token_apex}"}

    # Login as Beacon Registrar
    res_beacon = client.post("/api/auth/demo-login/2")
    assert res_beacon.status_code == 200
    token_beacon = res_beacon.json()["access_token"]
    headers_beacon = {"Authorization": f"Bearer {token_beacon}"}

    # 1. Apex Registrar tries to list Beacon's students by passing institution_id=inst-beacon-2002
    leak_res = client.get("/api/v1/students?institution_id=inst-beacon-2002", headers=headers_apex)
    # The endpoint enforces scope so it only returns Apex's own students
    assert leak_res.status_code == 200
    for s in leak_res.json()["items"]:
        assert s["institution_id"] == "inst-apex-1001"

    # 2. Apex Registrar tries to create student directly inside Beacon College
    hacker_create = {
        "student_name": "Intruder Student",
        "date_of_birth": "2004-01-01",
        "gender": "MALE",
        "category": "GENERAL",
        "internal_student_id": "INTRUDER-001",
        "course_id": "CRS-CSE",
        "academic_year": "2024-2025",
        "admission_year": 2024,
        "apaar_id": "829104829204",
        "is_supernumerary": False,
        "supernumerary_type": "NONE"
    }
    forbidden_create = client.post("/api/v1/students?institution_id=inst-beacon-2002", json=hacker_create, headers=headers_apex)
    assert forbidden_create.status_code == 403
    assert "Tenant isolation" in forbidden_create.json()["detail"]

    # 3. Beacon Registrar tries to edit Aarav Sharma (Apex student)
    forbidden_edit = client.put(
        "/api/v1/students/enrol-uuid-aarav-apex-cse",
        json={
            "student_name": "Hacked Name",
            "date_of_birth": "2004-01-01",
            "gender": "MALE",
            "category": "GENERAL",
            "internal_student_id": "AIT-2024-CSE-007",
            "course_id": "CRS-CSE",
            "academic_year": "2024-2025",
            "admission_year": 2024,
            "admission_status": "ENROLLED",
            "is_supernumerary": False,
            "supernumerary_type": "NONE",
            "nri_status": False,
            "oci_status": False,
            "foreign_national_status": False
        },
        headers=headers_beacon
    )
    assert forbidden_edit.status_code == 403
    assert "Tenant isolation" in forbidden_edit.json()["detail"]
