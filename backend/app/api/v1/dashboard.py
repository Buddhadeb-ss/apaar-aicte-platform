from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, case
from ..deps import get_db, require_role
from ...database.models import (
    Institution, InstitutionIntake, Student, StudentEnrolment,
    VerificationRequest, AuditEvent, Programme, Course, User, ValidationIssue,
    BulkUploadJob
)
from ...schemas.v1_schemas import (
    NationalDashboardMetrics, DuplicateCollisionAlert,
    AicteCommandCenterSummary, SeverityCounts, RecentUploadJobSummary,
    RecentVerificationSummary, ExcessInstitutionSummary,
    AicteAnalyticsResponse, StateEnrolmentStat, ProgrammeEnrolmentStat,
    AcademicYearTrendStat, InstitutionIntakeVsEnrolmentStat,
    CategoryBreakdownStat, QuotaBreakdownStat, ValidationIssueTrendStat,
    InstitutionDataCompletenessStat, TopInstitutionReviewStat
)
from ...core.validation_engine import ValidationEngine

router = APIRouter(prefix="/dashboard", tags=["National Regulatory Dashboard & Analytics"])

def _calculate_completeness(students: List[Student]) -> float:
    """Calculate percentage completeness across student identity and enrolment fields."""
    if not students:
        return 0.0
    total_fields = 0
    filled_fields = 0
    for s in students:
        # Identity checks: name, dob, gender, category, apaar
        total_fields += 5
        if s.student_name and s.student_name.strip():
            filled_fields += 1
        if s.date_of_birth and s.date_of_birth.strip():
            filled_fields += 1
        if s.gender and s.gender.strip():
            filled_fields += 1
        if s.category and s.category.strip():
            filled_fields += 1
        if s.apaar_hash or s.apaar_id_encrypted:
            filled_fields += 1
        
        # Enrolment checks
        if s.enrolments:
            e = s.enrolments[0]
            total_fields += 4
            if e.internal_student_id and e.internal_student_id.strip():
                filled_fields += 1
            if e.course_id:
                filled_fields += 1
            if e.academic_year:
                filled_fields += 1
            if e.admission_status:
                filled_fields += 1
    return round((filled_fields / total_fields * 100), 1) if total_fields > 0 else 0.0

@router.get("/command-center", response_model=AicteCommandCenterSummary)
def get_command_center_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["AICTE_ADMIN"]))
):
    """
    Central AICTE Command Center Summary:
    Strictly distinguishes unique student identities from active seat enrolments,
    aggregates approved intake vs utilization, supernumerary admissions,
    unresolved issues by severity, cross-institution collisions, excess enrolments,
    recent bulk upload imports, and data completeness.
    """
    engine = ValidationEngine()
    total_inst = db.query(Institution).filter(Institution.is_active == True).count()
    
    # 1. Distinct Physical Identities vs Active Enrolments
    total_identities = db.query(Student.id).distinct().count()
    total_active_enrolments = db.query(StudentEnrolment).filter(
        StudentEnrolment.admission_status.in_(engine.intake_policy.active_admission_statuses)
    ).count()

    total_approved = db.query(func.coalesce(func.sum(InstitutionIntake.approved_intake), 0)).scalar()
    utilization_pct = round((total_active_enrolments / total_approved * 100), 2) if total_approved > 0 else 0.0

    # 2. Supernumerary Admissions
    total_supernumerary = db.query(StudentEnrolment).filter(
        StudentEnrolment.is_supernumerary == True,
        StudentEnrolment.admission_status.in_(engine.intake_policy.active_admission_statuses)
    ).count()

    # 3. Pending Validation Issues by Severity
    unresolved_query = db.query(ValidationIssue).filter(
        ValidationIssue.resolution_status.in_(["NEW", "PENDING", "UNDER_REVIEW"])
    )
    crit_count = unresolved_query.filter(ValidationIssue.severity == "CRITICAL").count()
    high_count = unresolved_query.filter(ValidationIssue.severity == "HIGH").count()
    med_count = unresolved_query.filter(ValidationIssue.severity == "MEDIUM").count()
    low_count = unresolved_query.filter(ValidationIssue.severity == "LOW").count()
    pending_severity = SeverityCounts(
        critical=crit_count,
        high=high_count,
        medium=med_count,
        low=low_count,
        total=crit_count + high_count + med_count + low_count
    )

    # 4. Duplicate / Cross-Institution Collisions
    collision_groups = db.query(
        StudentEnrolment.student_id
    ).filter(
        StudentEnrolment.admission_status.in_(engine.intake_policy.active_admission_statuses)
    ).group_by(StudentEnrolment.student_id).having(func.count(func.distinct(StudentEnrolment.institution_id)) > 1).all()
    duplicate_alerts_count = len(collision_groups)

    # 5. Institutions with Excess Enrolment
    excess_institutions: List[ExcessInstitutionSummary] = []
    active_institutions = db.query(Institution).filter(Institution.is_active == True).all()
    for inst in active_institutions:
        inst_approved = db.query(func.coalesce(func.sum(InstitutionIntake.approved_intake), 0)).filter(
            InstitutionIntake.institution_id == inst.id
        ).scalar()
        inst_enrolled = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == inst.id,
            StudentEnrolment.is_supernumerary == False,
            StudentEnrolment.admission_status.in_(engine.intake_policy.active_admission_statuses)
        ).count()
        if inst_approved > 0 and inst_enrolled > inst_approved:
            excess_institutions.append(ExcessInstitutionSummary(
                institution_id=inst.id,
                institution_name=inst.name,
                aicte_id=inst.aicte_permanent_id,
                state=inst.state,
                approved_intake=inst_approved,
                enrolled_count=inst_enrolled,
                excess_count=inst_enrolled - inst_approved
            ))

    # 6. Recent Uploads & Failed Imports
    recent_jobs_db = db.query(BulkUploadJob).order_by(BulkUploadJob.created_at.desc()).limit(6).all()
    recent_uploads = [
        RecentUploadJobSummary(
            id=job.id,
            filename=job.filename,
            institution_id=job.institution_id,
            institution_name=job.institution.name if job.institution else "Unknown Institution",
            academic_year=job.academic_year,
            status=job.status,
            total_records=job.total_records,
            valid_records=job.valid_records,
            error_records=job.error_records,
            created_at=job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else ""
        )
        for job in recent_jobs_db
    ]
    failed_import_jobs_count = db.query(BulkUploadJob).filter(
        BulkUploadJob.status.in_(["FAILED", "REQUIRES_RESOLUTION"])
    ).count()

    # 7. Recent Verification Requests
    recent_verifs_db = db.query(VerificationRequest).order_by(VerificationRequest.created_at.desc()).limit(6).all()
    recent_verifications = [
        RecentVerificationSummary(
            id=v.id,
            token=v.token,
            verifier_name=v.verifier_name,
            verifier_organization=v.verifier_organization,
            purpose=v.purpose,
            verification_result=v.verification_result,
            student_name=v.student.student_name if v.student else "Unknown",
            apaar_masked=v.student.apaar_masked if v.student else "•••• •••• ••••",
            institution_name=v.enrolment.institution.name if (v.enrolment and v.enrolment.institution) else "National Registry",
            created_at=v.created_at.strftime("%Y-%m-%d %H:%M:%S") if v.created_at else ""
        )
        for v in recent_verifs_db
    ]

    # 8. Data Completeness Percentage
    all_students = db.query(Student).all()
    data_completeness = _calculate_completeness(all_students)

    return AicteCommandCenterSummary(
        total_registered_institutions=total_inst,
        total_student_identities=total_identities,
        total_active_enrolments=total_active_enrolments,
        total_approved_intake=total_approved,
        intake_utilization_pct=utilization_pct,
        total_supernumerary_admissions=total_supernumerary,
        pending_validation_issues=pending_severity,
        duplicate_alerts_count=duplicate_alerts_count,
        institutions_with_excess_enrolment=len(excess_institutions),
        excess_institutions=excess_institutions,
        recent_uploads=recent_uploads,
        failed_import_jobs_count=failed_import_jobs_count,
        recent_verification_requests=recent_verifications,
        data_completeness_pct=data_completeness,
        is_synthetic_data=True
    )

@router.get("/analytics", response_model=AicteAnalyticsResponse)
def get_dashboard_analytics(
    academic_year: Optional[str] = Query(None),
    programme_id: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["AICTE_ADMIN"]))
):
    """
    Dynamic Statutory Analytics Engine:
    Accepts filters for academic year, programme, and state.
    Computes live aggregations across state distribution, course enrolments,
    academic trends, category breakdowns, validation issues, and explainable review rankings.
    """
    engine = ValidationEngine()
    active_statuses = engine.intake_policy.active_admission_statuses

    # Base queries
    inst_query = db.query(Institution).filter(Institution.is_active == True)
    if state and state.upper() != "ALL":
        inst_query = inst_query.filter(Institution.state.ilike(f"%{state.strip()}%"))
    institutions = inst_query.all()
    inst_ids = [inst.id for inst in institutions]

    # 1. State / Regional Enrolment Breakdown
    state_map: Dict[str, Dict[str, Any]] = {}
    for inst in institutions:
        st_name = inst.state
        if st_name not in state_map:
            state_map[st_name] = {
                "approved": 0, "enrolled": 0, "supernumerary": 0, "inst_count": 0
            }
        state_map[st_name]["inst_count"] += 1

        # Intakes for this institution
        intake_q = db.query(func.coalesce(func.sum(InstitutionIntake.approved_intake), 0)).filter(
            InstitutionIntake.institution_id == inst.id
        )
        if academic_year and academic_year.upper() != "ALL":
            intake_q = intake_q.filter(InstitutionIntake.academic_year == academic_year)
        if programme_id and programme_id.upper() != "ALL":
            intake_q = intake_q.filter(InstitutionIntake.programme_id == programme_id)
        state_map[st_name]["approved"] += intake_q.scalar()

        # Enrolments
        enrol_q = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == inst.id,
            StudentEnrolment.admission_status.in_(active_statuses)
        )
        if academic_year and academic_year.upper() != "ALL":
            enrol_q = enrol_q.filter(StudentEnrolment.academic_year == academic_year)
        if programme_id and programme_id.upper() != "ALL":
            enrol_q = enrol_q.join(Course).filter(Course.programme_id == programme_id)

        all_enrols = enrol_q.all()
        for e in all_enrols:
            if e.is_supernumerary:
                state_map[st_name]["supernumerary"] += 1
            else:
                state_map[st_name]["enrolled"] += 1

    state_stats = [
        StateEnrolmentStat(
            state=st,
            approved_intake=vals["approved"],
            actual_enrolment=vals["enrolled"],
            supernumerary_enrolment=vals["supernumerary"],
            institutions_count=vals["inst_count"],
            utilization_rate=round((vals["enrolled"] / vals["approved"] * 100), 1) if vals["approved"] > 0 else 0.0
        )
        for st, vals in sorted(state_map.items())
    ]

    # 2. Programme-wise Enrolment Breakdown
    prog_query = db.query(Programme)
    if programme_id and programme_id.upper() != "ALL":
        prog_query = prog_query.filter(Programme.id == programme_id)
    programmes = prog_query.all()

    programme_stats = []
    for prog in programmes:
        intake_q = db.query(func.coalesce(func.sum(InstitutionIntake.approved_intake), 0)).filter(
            InstitutionIntake.programme_id == prog.id,
            InstitutionIntake.institution_id.in_(inst_ids) if inst_ids else True
        )
        if academic_year and academic_year.upper() != "ALL":
            intake_q = intake_q.filter(InstitutionIntake.academic_year == academic_year)
        p_approved = intake_q.scalar()

        enrol_q = db.query(StudentEnrolment).join(Course).filter(
            Course.programme_id == prog.id,
            StudentEnrolment.admission_status.in_(active_statuses),
            StudentEnrolment.institution_id.in_(inst_ids) if inst_ids else True
        )
        if academic_year and academic_year.upper() != "ALL":
            enrol_q = enrol_q.filter(StudentEnrolment.academic_year == academic_year)

        all_p_enrols = enrol_q.all()
        reg_count = sum(1 for e in all_p_enrols if not e.is_supernumerary)
        super_count = sum(1 for e in all_p_enrols if e.is_supernumerary)
        occ = round((reg_count / p_approved * 100), 1) if p_approved > 0 else 0.0

        programme_stats.append(ProgrammeEnrolmentStat(
            programme_id=prog.id,
            programme_name=prog.name,
            programme_code=prog.code,
            approved_intake=p_approved,
            actual_enrolment=reg_count,
            supernumerary_enrolment=super_count,
            utilization_rate=occ
        ))

    # 3. Academic Year Trends
    all_years = ["2022-2023", "2023-2024", "2024-2025"]
    year_stats = []
    for yr in all_years:
        y_app = db.query(func.coalesce(func.sum(InstitutionIntake.approved_intake), 0)).filter(
            InstitutionIntake.academic_year == yr,
            InstitutionIntake.institution_id.in_(inst_ids) if inst_ids else True
        ).scalar()
        y_enrols = db.query(StudentEnrolment).filter(
            StudentEnrolment.academic_year == yr,
            StudentEnrolment.admission_status.in_(active_statuses),
            StudentEnrolment.institution_id.in_(inst_ids) if inst_ids else True
        ).all()
        reg = sum(1 for e in y_enrols if not e.is_supernumerary)
        sup = sum(1 for e in y_enrols if e.is_supernumerary)
        occ = round((reg / y_app * 100), 1) if y_app > 0 else 0.0
        year_stats.append(AcademicYearTrendStat(
            academic_year=yr,
            approved_intake=y_app,
            actual_enrolment=reg,
            supernumerary=sup,
            utilization_rate=occ
        ))

    # 4. Institution Intake vs Enrolment
    inst_vs_enrol_stats = []
    for inst in institutions:
        i_app_q = db.query(func.coalesce(func.sum(InstitutionIntake.approved_intake), 0)).filter(
            InstitutionIntake.institution_id == inst.id
        )
        if academic_year and academic_year.upper() != "ALL":
            i_app_q = i_app_q.filter(InstitutionIntake.academic_year == academic_year)
        if programme_id and programme_id.upper() != "ALL":
            i_app_q = i_app_q.filter(InstitutionIntake.programme_id == programme_id)
        i_app = i_app_q.scalar()

        i_enrol_q = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == inst.id,
            StudentEnrolment.admission_status.in_(active_statuses)
        )
        if academic_year and academic_year.upper() != "ALL":
            i_enrol_q = i_enrol_q.filter(StudentEnrolment.academic_year == academic_year)
        if programme_id and programme_id.upper() != "ALL":
            i_enrol_q = i_enrol_q.join(Course).filter(Course.programme_id == programme_id)

        all_e = i_enrol_q.all()
        reg = sum(1 for e in all_e if not e.is_supernumerary)
        sup = sum(1 for e in all_e if e.is_supernumerary)
        occ = round((reg / i_app * 100), 1) if i_app > 0 else 0.0
        is_over = reg > i_app if i_app > 0 else False

        inst_vs_enrol_stats.append(InstitutionIntakeVsEnrolmentStat(
            institution_id=inst.id,
            institution_name=inst.name,
            aicte_id=inst.aicte_permanent_id,
            state=inst.state,
            approved_intake=i_app,
            actual_enrolment=reg,
            supernumerary=sup,
            utilization_rate=occ,
            is_over_admitted=is_over
        ))

    # 5. Category Breakdown (GENERAL, OBC, SC, ST, EWS)
    cat_query = db.query(Student.category, func.count(Student.id)).group_by(Student.category).all()
    total_studs = sum(c[1] for c in cat_query) or 1
    category_stats = [
        CategoryBreakdownStat(
            category=c[0] or "GENERAL",
            count=c[1],
            percentage=round(c[1] / total_studs * 100, 1)
        )
        for c in cat_query
    ]

    # 6. Quota Breakdown (Regular vs Supernumerary Categories)
    enrol_all = db.query(StudentEnrolment).filter(
        StudentEnrolment.admission_status.in_(active_statuses),
        StudentEnrolment.institution_id.in_(inst_ids) if inst_ids else True
    ).all()
    quota_counts: Dict[str, int] = {
        "Core Regular Intake": 0,
        "Tuition Fee Waiver (TFW)": 0,
        "NRI Quota": 0,
        "Foreign National / PIO": 0,
        "Other Supernumerary": 0
    }
    for e in enrol_all:
        if not e.is_supernumerary:
            quota_counts["Core Regular Intake"] += 1
        elif e.supernumerary_type == "TFW":
            quota_counts["Tuition Fee Waiver (TFW)"] += 1
        elif e.supernumerary_type == "NRI":
            quota_counts["NRI Quota"] += 1
        elif e.supernumerary_type == "FOREIGN_NATIONAL":
            quota_counts["Foreign National / PIO"] += 1
        else:
            quota_counts["Other Supernumerary"] += 1

    total_quotas = sum(quota_counts.values()) or 1
    quota_stats = [
        QuotaBreakdownStat(
            quota=q_name,
            count=cnt,
            percentage=round(cnt / total_quotas * 100, 1)
        )
        for q_name, cnt in quota_counts.items()
    ]

    # 7. Validation Issue Trends
    iss_query = db.query(
        ValidationIssue.rule_id,
        ValidationIssue.severity,
        func.count(ValidationIssue.id).label("total"),
        func.sum(
            case(
                (ValidationIssue.resolution_status.in_(["NEW", "PENDING", "UNDER_REVIEW"]), 1),
                else_=0
            )
        ).label("unresolved")
    ).filter(
        ValidationIssue.institution_id.in_(inst_ids) if inst_ids else True
    ).group_by(ValidationIssue.rule_id, ValidationIssue.severity).all()

    rule_names = {
        "RULE_MISSING_APAAR": "Missing APAAR ID",
        "RULE_MALFORMED_APAAR": "Malformed APAAR Checksum",
        "RULE_DUPLICATE_APAAR_INSTITUTION": "Internal APAAR Duplicate",
        "RULE_CROSS_INSTITUTION_DUPLICATE": "Cross-Institution Collision",
        "RULE_DUPLICATE_INTERNAL_IDENTIFIER": "Duplicate Roll Identifier",
        "RULE_MISSING_MANDATORY_FIELD": "Missing Mandatory Field",
        "RULE_INVALID_ACADEMIC_YEAR": "Invalid Academic Year",
        "RULE_INCONSISTENT_PROGRAMME_INSTITUTION": "Course/Institution Mismatch",
        "RULE_EXCESS_INTAKE_ENROLMENT": "Sanctioned Intake Exceeded",
        "RULE_SUPERNUMERARY_QUOTA_EXCEEDED": "Supernumerary Quota Overflow",
        "RULE_INCONSISTENT_NATIONALITY_DATA": "Nationality Data Inconsistency",
        "RULE_CONFLICTING_STUDENT_ATTRIBUTES": "Conflicting Student Attributes",
        "RULE_INVALID_ADMISSION_CATEGORY": "Invalid Category Alignment",
        "RULE_UNKNOWN": "General Regulatory Discrepancy"
    }

    validation_issue_trends = [
        ValidationIssueTrendStat(
            rule_id=r[0] or "RULE_UNKNOWN",
            rule_name=rule_names.get(r[0], r[0] or "Regulatory Rule"),
            severity=r[1] or "HIGH",
            total_count=r[2],
            unresolved_count=r[3] or 0
        )
        for r in iss_query
    ]

    # 8. Data Completeness by Institution
    completeness_stats = []
    for inst in institutions:
        inst_students = db.query(Student).join(StudentEnrolment).filter(
            StudentEnrolment.institution_id == inst.id
        ).distinct().all()
        pct = _calculate_completeness(inst_students)
        completeness_stats.append(InstitutionDataCompletenessStat(
            institution_id=inst.id,
            institution_name=inst.name,
            aicte_id=inst.aicte_permanent_id,
            total_students=len(inst_students),
            completeness_pct=pct
        ))

    # 9. Top Institutions Requiring Review (Explainable Statutory Scoring)
    review_items = []
    for inst in institutions:
        risk_score = 0.0
        flags = []

        # Check excess intake
        i_app = db.query(func.coalesce(func.sum(InstitutionIntake.approved_intake), 0)).filter(
            InstitutionIntake.institution_id == inst.id
        ).scalar()
        i_reg = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == inst.id,
            StudentEnrolment.is_supernumerary == False,
            StudentEnrolment.admission_status.in_(active_statuses)
        ).count()
        over_count = max(0, i_reg - i_app) if i_app > 0 else 0
        if over_count > 0:
            risk_score += 35.0
            flags.append(f"Sanctioned Intake Exceeded by {over_count} (+35)")

        # Check unresolved issues
        crit_issues = db.query(ValidationIssue).filter(
            ValidationIssue.institution_id == inst.id,
            ValidationIssue.severity == "CRITICAL",
            ValidationIssue.resolution_status.in_(["NEW", "PENDING", "UNDER_REVIEW"])
        ).count()
        if crit_issues > 0:
            risk_score += min(30.0, crit_issues * 15.0)
            flags.append(f"{crit_issues} Critical Validation Issues (+{min(30, crit_issues * 15)})")

        high_issues = db.query(ValidationIssue).filter(
            ValidationIssue.institution_id == inst.id,
            ValidationIssue.severity == "HIGH",
            ValidationIssue.resolution_status.in_(["NEW", "PENDING", "UNDER_REVIEW"])
        ).count()
        if high_issues > 0:
            risk_score += min(20.0, high_issues * 8.0)
            flags.append(f"{high_issues} High Severity Issues (+{min(20, high_issues * 8)})")

        # Check cross-institution collisions
        inst_collisions = db.query(StudentEnrolment.student_id).filter(
            StudentEnrolment.institution_id == inst.id,
            StudentEnrolment.admission_status.in_(active_statuses)
        ).group_by(StudentEnrolment.student_id).having(
            func.count(func.distinct(StudentEnrolment.institution_id)) > 1
        ).count()
        if inst_collisions > 0:
            risk_score += 25.0
            flags.append(f"Concurrent Cross-Institution Collision ({inst_collisions} students) (+25)")

        # Completeness penalty
        inst_studs = db.query(Student).join(StudentEnrolment).filter(
            StudentEnrolment.institution_id == inst.id
        ).distinct().all()
        comp = _calculate_completeness(inst_studs)
        if comp < 90.0:
            risk_score += 10.0
            flags.append(f"Sub-optimal Record Completeness ({comp}%) (+10)")

        risk_score = round(risk_score, 1)
        if risk_score >= 50.0:
            risk_lvl = "CRITICAL"
        elif risk_score >= 30.0:
            risk_lvl = "HIGH"
        elif risk_score >= 15.0:
            risk_lvl = "MEDIUM"
        else:
            risk_lvl = "LOW"

        if not flags:
            flags.append("Statutory Compliance Verified (Zero Active Flags)")

        review_items.append(TopInstitutionReviewStat(
            institution_id=inst.id,
            institution_name=inst.name,
            aicte_id=inst.aicte_permanent_id,
            state=inst.state,
            risk_score=risk_score,
            risk_level=risk_lvl,
            flags=flags,
            over_admitted_count=over_count,
            critical_issues_count=crit_issues,
            collision_count=inst_collisions,
            completeness_pct=comp
        ))

    review_items.sort(key=lambda x: x.risk_score, reverse=True)

    return AicteAnalyticsResponse(
        academic_year_filter=academic_year,
        programme_filter=programme_id,
        state_filter=state,
        enrolment_by_state=state_stats,
        programme_wise_enrolment=programme_stats,
        academic_year_trends=year_stats,
        institution_intake_vs_enrolment=inst_vs_enrol_stats,
        category_breakdown=category_stats,
        quota_breakdown=quota_stats,
        validation_issue_trends=validation_issue_trends,
        data_completeness_by_institution=completeness_stats,
        top_institutions_requiring_review=review_items,
        is_synthetic_data=True
    )

@router.get("/metrics", response_model=NationalDashboardMetrics)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["AICTE_ADMIN"]))
):
    """
    Returns aggregated national statistics strictly separating approved intake limits
    from student enrolment numbers. Uses ValidationEngine for active enrolment and intake reconciliation.
    """
    engine = ValidationEngine()
    total_approved = db.query(func.coalesce(func.sum(InstitutionIntake.approved_intake), 0)).scalar()

    total_institutions = db.query(Institution).filter(Institution.is_active == True).count()
    total_programmes = db.query(Programme).count()
    total_courses = db.query(Course).count()

    all_intakes = db.query(InstitutionIntake).all()
    total_enrolled = 0
    total_supernumerary = 0
    over_admission_count = 0

    for intake in all_intakes:
        intake_data = engine.calculate_actual_intake(
            db, intake.institution_id, intake.academic_year, course_id=intake.course_id
        )
        total_enrolled += intake_data["regular_active_enrolled"]
        total_supernumerary += intake_data["supernumerary_active_enrolled"]
        if intake_data["regular_active_enrolled"] > intake.approved_intake:
            over_admission_count += 1

    duplicate_groups = db.query(
        StudentEnrolment.student_id,
        func.count(func.distinct(StudentEnrolment.institution_id)).label("inst_count")
    ).filter(
        StudentEnrolment.admission_status.in_(engine.intake_policy.active_admission_statuses)
    ).group_by(StudentEnrolment.student_id).having(func.count(func.distinct(StudentEnrolment.institution_id)) > 1).all()

    duplicate_apaar_count = len(duplicate_groups)

    total_issues = db.query(ValidationIssue).count()
    critical_issues = db.query(ValidationIssue).filter(ValidationIssue.severity == "CRITICAL").count()
    unresolved_issues = db.query(ValidationIssue).filter(
        ValidationIssue.resolution_status.in_(["NEW", "PENDING", "UNDER_REVIEW"])
    ).count()

    total_verifications = db.query(VerificationRequest).count()

    recent_audits = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(8).all()
    audit_list = [
        {
            "id": a.id,
            "event_type": a.event_type,
            "actor_role": a.actor_role,
            "actor_email": a.actor_email,
            "institution_id": a.institution_id,
            "details": a.details_json,
            "timestamp": a.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }
        for a in recent_audits
    ]

    occupancy_rate = round((total_enrolled / total_approved * 100), 2) if total_approved > 0 else 0.0

    return NationalDashboardMetrics(
        total_institutions=total_institutions,
        total_programmes=total_programmes or 1,
        total_courses=total_courses or 1,
        total_approved_intake=total_approved,
        total_actual_enrolled=total_enrolled,
        total_supernumerary_enrolled=total_supernumerary,
        overall_occupancy_rate=occupancy_rate,
        over_admission_violations=over_admission_count,
        duplicate_apaar_violations=duplicate_apaar_count,
        total_verifications_performed=total_verifications,
        recent_audit_events=audit_list,
        total_validation_issues=total_issues,
        critical_validation_issues=critical_issues,
        unresolved_validation_issues=unresolved_issues
    )

@router.get("/duplicates", response_model=List[DuplicateCollisionAlert])
def get_duplicate_collision_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["AICTE_ADMIN"]))
):
    """
    Central Registry Collision Detector:
    Scans for any student holding active enrolments across multiple technical institutions.
    """
    collision_student_ids = db.query(StudentEnrolment.student_id).group_by(
        StudentEnrolment.student_id
    ).having(func.count(func.distinct(StudentEnrolment.institution_id)) > 1).all()

    alerts = []
    for (sid,) in collision_student_ids:
        st = db.query(Student).filter(Student.id == sid).first()
        if not st:
            continue

        enrols = db.query(StudentEnrolment).filter(StudentEnrolment.student_id == sid).all()
        enrol_data = [
            {
                "institution_id": e.institution_id,
                "institution_name": e.institution.name if e.institution else "Unknown",
                "course": e.course.name if e.course else "Unknown",
                "internal_id": e.internal_student_id,
                "academic_year": e.academic_year,
                "status": e.record_status
            }
            for e in enrols
        ]

        alerts.append(DuplicateCollisionAlert(
            apaar_hash=st.apaar_hash,
            apaar_masked=st.apaar_masked,
            student_name=st.student_name,
            student_id=st.id,
            enrolments=enrol_data,
            flag="CONCURRENT_ENROLMENT_DISCREPANCY"
        ))

    return alerts
