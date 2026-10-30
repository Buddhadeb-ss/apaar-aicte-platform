import urllib.request
import urllib.error
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def post_json(endpoint, data):
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_json(endpoint, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE_URL}{endpoint}", headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_expect_error(endpoint, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE_URL}{endpoint}", headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")

def main():
    print("=" * 70)
    print("SIH26263 ACCEPTANCE VERIFICATION: AICTE COMMAND CENTER & INSTITUTION DASHBOARDS")
    print("=" * 70)

    # 1. Login as AICTE Administrator
    print("\n[Step 1] Authenticating as AICTE Administrator...")
    aicte_login = post_json("/auth/login", {
        "email": "admin@aicte.gov.in",
        "password": "Aicte@2026"
    })
    aicte_token = aicte_login["access_token"]
    print(f" -> AICTE Admin Logged In: {aicte_login['name']} (Role: {aicte_login['role']})")

    # 2. Fetch AICTE Command Center Dashboard
    print("\n[Step 2] Testing AICTE Command Center Summary...")
    command_center = get_json("/dashboard/command-center", token=aicte_token)
    print(f" -> Total Registered Institutions: {command_center['total_registered_institutions']}")
    print(f" -> Total Student Identities:     {command_center['total_student_identities']}")
    print(f" -> Total Active Enrolments:      {command_center['total_active_enrolments']}")
    print(f" -> Total Approved Intake:        {command_center['total_approved_intake']}")
    print(f" -> Intake Utilization:           {command_center['intake_utilization_pct']}%")
    print(f" -> Supernumerary Admissions:     {command_center['total_supernumerary_admissions']}")
    print(f" -> Pending Issues by Severity:   {command_center['pending_validation_issues']}")
    print(f" -> Cross-Inst Collision Alerts:  {command_center['duplicate_alerts_count']}")
    print(f" -> Excess Enrolment Campuses:    {command_center['institutions_with_excess_enrolment']}")
    print(f" -> Recent Upload Jobs:           {len(command_center['recent_uploads'])}")
    print(f" -> Failed Import Jobs:           {command_center['failed_import_jobs_count']}")
    print(f" -> Recent Verifications:         {len(command_center['recent_verification_requests'])}")
    print(f" -> Data Completeness Percentage: {command_center['data_completeness_pct']}%")

    # Assertions for AICTE Command Center
    assert command_center['total_registered_institutions'] >= 3, "Expected at least 3 institutions"
    assert command_center['total_student_identities'] == 16, f"Expected 16 identities, got {command_center['total_student_identities']}"
    assert command_center['total_active_enrolments'] == 17, f"Expected 17 enrolments, got {command_center['total_active_enrolments']}"
    assert command_center['total_student_identities'] < command_center['total_active_enrolments'], "Identities and enrolments must be distinctly computed!"
    assert command_center['duplicate_alerts_count'] >= 1, "Expected duplicate cross-institution collision"
    assert command_center['recent_uploads'], "Expected recent bulk upload history"
    assert command_center['recent_verification_requests'], "Expected recent verification history"
    print(" [PASS] AICTE Command Center metrics verified successfully!")

    # 3. Test AICTE Analytics with dynamic filters
    print("\n[Step 3] Testing AICTE Statutory Analytics Engine with Dynamic Filters...")
    unfiltered_analytics = get_json("/dashboard/analytics", token=aicte_token)
    print(f" -> Unfiltered: {len(unfiltered_analytics['enrolment_by_state'])} states, {len(unfiltered_analytics['programme_wise_enrolment'])} programmes")
    print(f" -> Top Institutions Requiring Review: {len(unfiltered_analytics['top_institutions_requiring_review'])}")
    for top in unfiltered_analytics['top_institutions_requiring_review']:
        print(f"    - {top['institution_name']}: Risk Score = {top['risk_score']}, Flags: {', '.join(top['flags'])}")

    # Filter by Academic Year 2024-2025
    filtered_ay = get_json("/dashboard/analytics?academic_year=2024-2025", token=aicte_token)
    assert filtered_ay['academic_year_filter'] == '2024-2025'
    print(f" -> Academic Year Filter (2024-2025): Applied successfully")

    # Filter by State Maharashtra
    filtered_state = get_json("/dashboard/analytics?state=Maharashtra", token=aicte_token)
    assert filtered_state['state_filter'] == 'Maharashtra'
    print(f" -> State Filter (Maharashtra): Returned {len(filtered_state['enrolment_by_state'])} matching state row(s)")
    print(" [PASS] AICTE Dynamic Analytics verified successfully!")

    # 4. Authenticate as Institution 1: Apex Tech
    print("\n[Step 4] Authenticating as Institution 1 (Apex Institute of Technology)...")
    apex_login = post_json("/auth/login", {
        "email": "registrar@apex.edu",
        "password": "Apex@2026"
    })
    apex_token = apex_login["access_token"]
    apex_inst_id = apex_login["institution_id"]
    print(f" -> Apex Admin Logged In: {apex_login['name']} (Inst ID: {apex_inst_id})")

    apex_summary = get_json(f"/institutions/{apex_inst_id}/dashboard-summary", token=apex_token)
    print(f" -> Apex Approved Intake:        {apex_summary['total_approved_intake']}")
    print(f" -> Apex Regular Enrolment:      {apex_summary['total_actual_enrolled']}")
    print(f" -> Apex Supernumerary Enrolment:{apex_summary['total_supernumerary_enrolled']}")
    print(f" -> Apex Capacity Utilization:   {apex_summary['intake_utilization_pct']}%")
    print(f" -> Apex Programme Breakdown:    {len(apex_summary['programme_breakdown'])} courses")
    print(f" -> Apex Unresolved Issues:      {apex_summary['unresolved_issues_count']}")
    print(f" -> Apex Data Completeness:      {apex_summary['student_record_completeness_pct']}%")
    assert apex_summary['total_approved_intake'] == 300, f"Expected 300, got {apex_summary['total_approved_intake']}"
    print(" [PASS] Apex Tech Dashboard Summary verified!")

    # 5. Authenticate as Institution 2: Beacon College
    print("\n[Step 5] Authenticating as Institution 2 (Beacon College of Engineering)...")
    beacon_login = post_json("/auth/login", {
        "email": "principal@beacon.ac.in",
        "password": "Beacon@2026"
    })
    beacon_token = beacon_login["access_token"]
    beacon_inst_id = beacon_login["institution_id"]
    print(f" -> Beacon Admin Logged In: {beacon_login['name']} (Inst ID: {beacon_inst_id})")

    beacon_summary = get_json(f"/institutions/{beacon_inst_id}/dashboard-summary", token=beacon_token)
    print(f" -> Beacon Approved Intake:      {beacon_summary['total_approved_intake']}")
    print(f" -> Beacon Regular Enrolment:    {beacon_summary['total_actual_enrolled']}")
    print(f" -> Beacon Supernumerary Enrol:  {beacon_summary['total_supernumerary_enrolled']}")
    print(f" -> Beacon Capacity Utilization: {beacon_summary['intake_utilization_pct']}%")
    print(f" -> Beacon Programme Breakdown:  {len(beacon_summary['programme_breakdown'])} courses")
    print(f" -> Beacon Unresolved Issues:    {beacon_summary['unresolved_issues_count']}")
    print(f" -> Beacon Data Completeness:    {beacon_summary['student_record_completeness_pct']}%")
    assert beacon_summary['total_approved_intake'] == 120, f"Expected 120, got {beacon_summary['total_approved_intake']}"
    print(" [PASS] Beacon College Dashboard Summary verified!")

    # 6. Verify Strict Multi-Tenant Isolation
    print("\n[Step 6] Testing Cross-Tenant Security Isolation...")
    # Apex Admin attempts to access Beacon College summary -> Must be 403 Forbidden!
    status, err = get_expect_error(f"/institutions/{beacon_inst_id}/dashboard-summary", token=apex_token)
    print(f" -> Apex accessing Beacon Dashboard: HTTP {status}")
    assert status == 403, f"Expected 403 Forbidden, got {status}"

    # Beacon Admin attempts to access Apex Tech summary -> Must be 403 Forbidden!
    status, err = get_expect_error(f"/institutions/{apex_inst_id}/dashboard-summary", token=beacon_token)
    print(f" -> Beacon accessing Apex Dashboard: HTTP {status}")
    assert status == 403, f"Expected 403 Forbidden, got {status}"

    # AICTE Admin can access both without restriction
    aicte_access_apex = get_json(f"/institutions/{apex_inst_id}/dashboard-summary", token=aicte_token)
    aicte_access_beacon = get_json(f"/institutions/{beacon_inst_id}/dashboard-summary", token=aicte_token)
    assert aicte_access_apex['institution_id'] == apex_inst_id
    assert aicte_access_beacon['institution_id'] == beacon_inst_id
    print(" -> AICTE Admin accessing both campuses: HTTP 200 OK for both")
    print(" [PASS] Multi-tenant isolation verified with absolute security enforcement!")

    print("\n" + "=" * 70)
    print("ALL ACCEPTANCE CRITERIA VERIFIED AND PASSED SUCCESSFULLY (100%)")
    print("=" * 70)

if __name__ == "__main__":
    main()
