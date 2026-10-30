from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from ..deps import get_db, get_current_user, require_role, enforce_institution_scope
from ...database.models import (
    Institution, Programme, Course, InstitutionIntake, StudentEnrolment, User,
    Student, ValidationIssue, BulkUploadJob, VerificationRequest
)
from ...schemas.v1_schemas import (
    InstitutionOut, ProgrammeOut, CourseOut, CourseIntakeDetail, PaginatedResponse,
    InstitutionDashboardSummary, CourseIntakeOccupancyStat, RecentUploadJobSummary,
    RecentVerificationSummary, SeverityCounts
)
from ...core.identifiers import generate_uuid, normalize_identifier
from ...core.validation_engine import ValidationEngine

router = APIRouter(prefix="/institutions", tags=["Institutions & Programmes Management"])

@router.get("/programmes", response_model=List[ProgrammeOut])
def list_programmes(db: Session = Depends(get_db)):
    """List statutory AICTE programmes (Engineering, Management, Pharmacy, etc.)."""
    return db.query(Programme).order_by(Programme.name).all()

@router.get("/courses", response_model=List[CourseOut])
def list_courses(programme_id: Optional[str] = None, db: Session = Depends(get_db)):
    """List approved courses with optional programme filter."""
    query = db.query(Course)
    if programme_id:
        query = query.filter(Course.programme_id == programme_id)
    return query.order_by(Course.name).all()

@router.get("", response_model=PaginatedResponse[InstitutionOut])
def list_institutions(
    search: Optional[str] = None,
    state: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List AICTE-approved technical institutions with calculated sanctioned intake
    and confirmed student enrolment summaries.
    """
    query = db.query(Institution).filter(Institution.is_active == True)

    if current_user.role in ("INSTITUTION_ADMIN", "INSTITUTION_OPERATOR"):
        query = query.filter(Institution.id == current_user.institution_id)

    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Institution.name.ilike(search_fmt),
                Institution.aicte_permanent_id.ilike(search_fmt),
                Institution.district.ilike(search_fmt)
            )
        )
    if state:
        query = query.filter(Institution.state.ilike(f"%{state.strip()}%"))

    total = query.count()
    institutions = query.order_by(Institution.name).offset((page - 1) * limit).limit(limit).all()

    items = []
    for inst in institutions:
        total_approved = db.query(func.coalesce(func.sum(InstitutionIntake.approved_intake), 0)).filter(
            InstitutionIntake.institution_id == inst.id
        ).scalar()

        total_enrolled = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == inst.id,
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).count()

        intakes_query = db.query(InstitutionIntake).filter(InstitutionIntake.institution_id == inst.id).all()
        intake_details = []
        has_over_admission = False

        for ci in intakes_query:
            reg_enrolled = db.query(StudentEnrolment).filter(
                StudentEnrolment.institution_id == inst.id,
                StudentEnrolment.course_id == ci.course_id,
                StudentEnrolment.is_supernumerary == False,
                StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
            ).count()

            super_enrolled = db.query(StudentEnrolment).filter(
                StudentEnrolment.institution_id == inst.id,
                StudentEnrolment.course_id == ci.course_id,
                StudentEnrolment.is_supernumerary == True,
                StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
            ).count()

            is_over = reg_enrolled > ci.approved_intake
            if is_over:
                has_over_admission = True

            occ = round((reg_enrolled / ci.approved_intake * 100), 1) if ci.approved_intake > 0 else 0.0

            intake_details.append(CourseIntakeDetail(
                id=ci.id,
                institution_id=ci.institution_id,
                course_id=ci.course_id,
                course_name=ci.course.name if ci.course else "Unknown Course",
                programme_name=ci.programme.name if ci.programme else "Unknown Programme",
                academic_year=ci.academic_year,
                approved_intake=ci.approved_intake,
                tfw_supernumerary_quota=ci.tfw_supernumerary_quota,
                nri_supernumerary_quota=ci.nri_supernumerary_quota,
                fn_supernumerary_quota=ci.fn_supernumerary_quota,
                actual_enrolment=reg_enrolled,
                actual_supernumerary=super_enrolled,
                occupancy_rate=occ,
                is_over_admitted=is_over
            ))

        items.append(InstitutionOut(
            id=inst.id,
            aicte_permanent_id=inst.aicte_permanent_id,
            name=inst.name,
            state=inst.state,
            district=inst.district,
            address=inst.address,
            institution_type=inst.institution_type,
            approval_session=inst.approval_session,
            contact_email=inst.contact_email,
            contact_phone=inst.contact_phone,
            total_approved_intake=total_approved,
            total_enrolled=total_enrolled,
            intake_status="NON_COMPLIANT_OVER_ADMISSION" if has_over_admission else "COMPLIANT",
            intakes=intake_details
        ))

    total_pages = (total + limit - 1) // limit if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

@router.get("/{id}", response_model=InstitutionOut)
def get_institution(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve institution profile and sanctioned course intakes."""
    enforce_institution_scope(current_user, id)
    inst = db.query(Institution).filter(Institution.id == id, Institution.is_active == True).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution record not found.")

    total_approved = db.query(func.coalesce(func.sum(InstitutionIntake.approved_intake), 0)).filter(
        InstitutionIntake.institution_id == inst.id
    ).scalar()

    total_enrolled = db.query(StudentEnrolment).filter(
        StudentEnrolment.institution_id == inst.id,
        StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
    ).count()

    intakes_query = db.query(InstitutionIntake).filter(InstitutionIntake.institution_id == inst.id).all()
    intake_details = []
    has_over_admission = False

    for ci in intakes_query:
        reg_enrolled = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == inst.id,
            StudentEnrolment.course_id == ci.course_id,
            StudentEnrolment.is_supernumerary == False,
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).count()

        super_enrolled = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == inst.id,
            StudentEnrolment.course_id == ci.course_id,
            StudentEnrolment.is_supernumerary == True,
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).count()

        is_over = reg_enrolled > ci.approved_intake
        if is_over:
            has_over_admission = True

        occ = round((reg_enrolled / ci.approved_intake * 100), 1) if ci.approved_intake > 0 else 0.0

        intake_details.append(CourseIntakeDetail(
            id=ci.id,
            institution_id=ci.institution_id,
            course_id=ci.course_id,
            course_name=ci.course.name if ci.course else "Unknown Course",
            programme_name=ci.programme.name if ci.programme else "Unknown Programme",
            academic_year=ci.academic_year,
            approved_intake=ci.approved_intake,
            tfw_supernumerary_quota=ci.tfw_supernumerary_quota,
            nri_supernumerary_quota=ci.nri_supernumerary_quota,
            fn_supernumerary_quota=ci.fn_supernumerary_quota,
            actual_enrolment=reg_enrolled,
            actual_supernumerary=super_enrolled,
            occupancy_rate=occ,
            is_over_admitted=is_over
        ))

    return InstitutionOut(
        id=inst.id,
        aicte_permanent_id=inst.aicte_permanent_id,
        name=inst.name,
        state=inst.state,
        district=inst.district,
        address=inst.address,
        institution_type=inst.institution_type,
        approval_session=inst.approval_session,
        contact_email=inst.contact_email,
        contact_phone=inst.contact_phone,
        total_approved_intake=total_approved,
        total_enrolled=total_enrolled,
        intake_status="NON_COMPLIANT_OVER_ADMISSION" if has_over_admission else "COMPLIANT",
        intakes=intake_details
    )

@router.get("/{id}/dashboard-summary", response_model=InstitutionDashboardSummary)
def get_institution_dashboard_summary(
    id: str,
    academic_year: Optional[str] = Query("2024-2025"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Institution-scoped Executive Dashboard Summary:
    Computes sanctioned intake, confirmed regular and supernumerary admissions,
    course-level utilization, student-record completeness, unresolved issues by severity,
    and recent upload job history isolated to the signed-in institution.
    """
    enforce_institution_scope(current_user, id)
    inst = db.query(Institution).filter(Institution.id == id, Institution.is_active == True).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution record not found.")

    engine = ValidationEngine()
    active_statuses = engine.intake_policy.active_admission_statuses

    # 1. Total Approved Intake & Actual Enrolments
    intake_q = db.query(InstitutionIntake).filter(InstitutionIntake.institution_id == inst.id)
    if academic_year and academic_year.upper() != "ALL":
        intake_q = intake_q.filter(InstitutionIntake.academic_year == academic_year)
    intakes = intake_q.all()

    total_approved = sum(i.approved_intake for i in intakes)
    
    enrol_q = db.query(StudentEnrolment).filter(
        StudentEnrolment.institution_id == inst.id,
        StudentEnrolment.admission_status.in_(active_statuses)
    )
    if academic_year and academic_year.upper() != "ALL":
        enrol_q = enrol_q.filter(StudentEnrolment.academic_year == academic_year)
    all_enrolments = enrol_q.all()

    total_regular = sum(1 for e in all_enrolments if not e.is_supernumerary)
    total_super = sum(1 for e in all_enrolments if e.is_supernumerary)
    utilization_pct = round((total_regular / total_approved * 100), 1) if total_approved > 0 else 0.0

    # 2. Programme / Course Breakdown
    programme_breakdown = []
    has_over_admission = False
    for ci in intakes:
        reg_count = sum(1 for e in all_enrolments if e.course_id == ci.course_id and not e.is_supernumerary)
        super_count = sum(1 for e in all_enrolments if e.course_id == ci.course_id and e.is_supernumerary)
        is_over = reg_count > ci.approved_intake
        if is_over:
            has_over_admission = True
        c_occ = round((reg_count / ci.approved_intake * 100), 1) if ci.approved_intake > 0 else 0.0

        programme_breakdown.append(CourseIntakeOccupancyStat(
            course_id=ci.course_id,
            course_name=ci.course.name if ci.course else "Unknown Course",
            degree=ci.course.degree if ci.course else "B.Tech",
            programme_name=ci.programme.name if ci.programme else "Engineering",
            approved_intake=ci.approved_intake,
            regular_enrolled=reg_count,
            supernumerary_enrolled=super_count,
            utilization_pct=c_occ,
            is_over_admitted=is_over
        ))

    # 3. Unresolved Validation Issues
    unresolved_q = db.query(ValidationIssue).filter(
        ValidationIssue.institution_id == inst.id,
        ValidationIssue.resolution_status.in_(["NEW", "PENDING", "UNDER_REVIEW"])
    )
    crit_c = unresolved_q.filter(ValidationIssue.severity == "CRITICAL").count()
    high_c = unresolved_q.filter(ValidationIssue.severity == "HIGH").count()
    med_c = unresolved_q.filter(ValidationIssue.severity == "MEDIUM").count()
    low_c = unresolved_q.filter(ValidationIssue.severity == "LOW").count()
    unresolved_count = crit_c + high_c + med_c + low_c
    severity_counts = SeverityCounts(
        critical=crit_c, high=high_c, medium=med_c, low=low_c, total=unresolved_count
    )

    # 4. Recent Upload Jobs for this Institution
    recent_jobs_db = db.query(BulkUploadJob).filter(
        BulkUploadJob.institution_id == inst.id
    ).order_by(BulkUploadJob.created_at.desc()).limit(6).all()
    recent_uploads = [
        RecentUploadJobSummary(
            id=job.id,
            filename=job.filename,
            institution_id=job.institution_id,
            institution_name=inst.name,
            academic_year=job.academic_year,
            status=job.status,
            total_records=job.total_records,
            valid_records=job.valid_records,
            error_records=job.error_records,
            created_at=job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else ""
        )
        for job in recent_jobs_db
    ]
    failed_jobs_count = db.query(BulkUploadJob).filter(
        BulkUploadJob.institution_id == inst.id,
        BulkUploadJob.status.in_(["FAILED", "REQUIRES_RESOLUTION"])
    ).count()

    # 5. Student Record Completeness Score & Missing Fields Breakdown
    inst_students = db.query(Student).join(StudentEnrolment).filter(
        StudentEnrolment.institution_id == inst.id
    ).distinct().all()

    missing_fields: Dict[str, int] = {
        "student_name": 0, "date_of_birth": 0, "gender": 0, "category": 0,
        "apaar_id": 0, "internal_student_id": 0
    }
    total_checks = 0
    filled_checks = 0
    for s in inst_students:
        total_checks += 6
        if s.student_name and s.student_name.strip(): filled_checks += 1
        else: missing_fields["student_name"] += 1
        
        if s.date_of_birth and s.date_of_birth.strip(): filled_checks += 1
        else: missing_fields["date_of_birth"] += 1
        
        if s.gender and s.gender.strip(): filled_checks += 1
        else: missing_fields["gender"] += 1
        
        if s.category and s.category.strip(): filled_checks += 1
        else: missing_fields["category"] += 1
        
        if s.apaar_hash or s.apaar_id_encrypted: filled_checks += 1
        else: missing_fields["apaar_id"] += 1
        
        if s.enrolments and s.enrolments[0].internal_student_id: filled_checks += 1
        else: missing_fields["internal_student_id"] += 1

    completeness_pct = round((filled_checks / total_checks * 100), 1) if total_checks > 0 else 0.0

    # 6. Recent Verification Requests for this institution's students
    verif_q = db.query(VerificationRequest).join(StudentEnrolment, VerificationRequest.enrolment_id == StudentEnrolment.id).filter(
        StudentEnrolment.institution_id == inst.id
    ).order_by(VerificationRequest.created_at.desc()).limit(5).all()

    recent_verifs = [
        RecentVerificationSummary(
            id=v.id,
            token=v.token,
            verifier_name=v.verifier_name,
            verifier_organization=v.verifier_organization,
            purpose=v.purpose,
            verification_result=v.verification_result,
            student_name=v.student.student_name if v.student else "Unknown",
            apaar_masked=v.student.apaar_masked if v.student else "•••• •••• ••••",
            institution_name=inst.name,
            created_at=v.created_at.strftime("%Y-%m-%d %H:%M:%S") if v.created_at else ""
        )
        for v in verif_q
    ]

    return InstitutionDashboardSummary(
        institution_id=inst.id,
        institution_name=inst.name,
        aicte_permanent_id=inst.aicte_permanent_id,
        state=inst.state,
        district=inst.district,
        approval_session=inst.approval_session,
        institution_type=inst.institution_type,
        contact_email=inst.contact_email,
        total_approved_intake=total_approved,
        total_actual_enrolled=total_regular,
        total_supernumerary_enrolled=total_super,
        intake_utilization_pct=utilization_pct,
        intake_compliance_status="NON_COMPLIANT_OVER_ADMISSION" if has_over_admission else "COMPLIANT",
        programme_breakdown=programme_breakdown,
        recent_uploads=recent_uploads,
        failed_import_jobs_count=failed_jobs_count,
        unresolved_issues_count=unresolved_count,
        unresolved_issues_by_severity=severity_counts,
        student_record_completeness_pct=completeness_pct,
        missing_fields_breakdown=missing_fields,
        recent_verifications=recent_verifs,
        is_synthetic_data=True
    )
