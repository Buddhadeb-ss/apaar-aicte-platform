import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.database.seed_data import seed_database

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    db = SessionLocal()
    seed_database(db, force_reset=True)
    db.close()

@pytest.fixture
def client():
    return TestClient(app)

def test_aicte_command_center_summary(client):
    """Verify AICTE Command Center distinguishes physical student identities from seat enrolments."""
    # Login as AICTE Admin
    login_res = client.post("/api/v1/auth/demo-login/0")
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/dashboard/command-center", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_registered_institutions"] == 3
    # Distinct identities vs active enrolments
    assert data["total_student_identities"] == 16
    assert data["total_active_enrolments"] == 17
    assert data["total_student_identities"] != data["total_active_enrolments"]
    
    assert data["total_approved_intake"] > 0
    assert data["intake_utilization_pct"] > 0.0
    assert data["total_supernumerary_admissions"] >= 3
    assert data["duplicate_alerts_count"] >= 1
    assert data["pending_validation_issues"]["total"] > 0
    assert len(data["recent_uploads"]) > 0
    assert data["failed_import_jobs_count"] >= 1
    assert data["data_completeness_pct"] > 50.0
    assert data["is_synthetic_data"] is True

def test_aicte_analytics_with_filters(client):
    """Verify statutory analytics responds dynamically to filters."""
    login_res = client.post("/api/v1/auth/demo-login/0")
    assert login_res.status_code == 200
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # 1. Unfiltered
    res1 = client.get("/api/v1/dashboard/analytics", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert len(data1["enrolment_by_state"]) >= 2
    assert len(data1["programme_wise_enrolment"]) >= 2
    assert len(data1["academic_year_trends"]) >= 3
    assert len(data1["category_breakdown"]) >= 1
    assert len(data1["quota_breakdown"]) >= 1
    assert len(data1["top_institutions_requiring_review"]) == 3
    # Verify explainable flags on review items
    assert all(len(item["flags"]) > 0 for item in data1["top_institutions_requiring_review"])

    # 2. Filtered by State
    res2 = client.get("/api/v1/dashboard/analytics?state=Maharashtra", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2["enrolment_by_state"]) == 1
    assert data2["enrolment_by_state"][0]["state"] == "Maharashtra"

    # 3. Filtered by Academic Year
    res3 = client.get("/api/v1/dashboard/analytics?academic_year=2024-2025", headers=headers)
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["academic_year_filter"] == "2024-2025"

def test_institution_dashboard_summary_and_isolation(client):
    """Verify institution dashboard summary isolation between Apex Tech and Beacon College."""
    # 1. Apex Tech Admin Login (Institution ID: inst-apex-1001)
    login_apex = client.post("/api/v1/auth/demo-login/1")
    assert login_apex.status_code == 200
    apex_headers = {"Authorization": f"Bearer {login_apex.json()['access_token']}"}

    # Apex accesses Apex -> 200 OK
    apex_res = client.get("/api/v1/institutions/inst-apex-1001/dashboard-summary", headers=apex_headers)
    assert apex_res.status_code == 200
    apex_data = apex_res.json()
    assert apex_data["institution_id"] == "inst-apex-1001"
    assert "Apex" in apex_data["institution_name"]
    assert apex_data["total_approved_intake"] == 300  # 120+60+60+60
    assert len(apex_data["programme_breakdown"]) == 4
    assert apex_data["student_record_completeness_pct"] > 0
    assert apex_data["is_synthetic_data"] is True

    # Apex attempts to access Beacon -> 403 Forbidden
    cross_res = client.get("/api/v1/institutions/inst-beacon-2002/dashboard-summary", headers=apex_headers)
    assert cross_res.status_code == 403

    # 2. Beacon College Admin Login (Institution ID: inst-beacon-2002)
    login_beacon = client.post("/api/v1/auth/demo-login/5")
    assert login_beacon.status_code == 200
    beacon_headers = {"Authorization": f"Bearer {login_beacon.json()['access_token']}"}

    # Beacon accesses Beacon -> 200 OK
    beacon_res = client.get("/api/v1/institutions/inst-beacon-2002/dashboard-summary", headers=beacon_headers)
    assert beacon_res.status_code == 200
    beacon_data = beacon_res.json()
    assert beacon_data["institution_id"] == "inst-beacon-2002"
    assert "Beacon" in beacon_data["institution_name"]
    assert beacon_data["total_approved_intake"] == 120  # 60+60

    # Beacon attempts to access Apex -> 403 Forbidden
    cross_res2 = client.get("/api/v1/institutions/inst-apex-1001/dashboard-summary", headers=beacon_headers)
    assert cross_res2.status_code == 403

    # 3. AICTE Admin can access both
    login_aicte = client.post("/api/v1/auth/demo-login/0")
    aicte_headers = {"Authorization": f"Bearer {login_aicte.json()['access_token']}"}
    assert client.get("/api/v1/institutions/inst-apex-1001/dashboard-summary", headers=aicte_headers).status_code == 200
    assert client.get("/api/v1/institutions/inst-beacon-2002/dashboard-summary", headers=aicte_headers).status_code == 200
