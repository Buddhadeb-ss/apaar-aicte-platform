from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from .deps import get_db, get_current_user, enforce_institution_scope
from ..database.models import User, Institution, InstitutionCourseIntake, Student, StudentEnrolment, AuditLog
from ..schemas.schemas import InstitutionOut, CourseIntakeOut, CourseIntakeBase

router = APIRouter(prefix="/institutions", tags=["Institutions & Intake Allocation"])

@router.get("/{institution_id}", response_model=InstitutionOut)
def get_institution_profile(
    institution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve institution profile details with course intakes."""
    enforce_institution_scope(current_user, institution_id)
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")

    total_approved = db.query(func.coalesce(func.sum(InstitutionCourseIntake.approved_intake), 0)).filter(
        InstitutionCourseIntake.institution_id == institution_id
    ).scalar()

    total_enrolled = db.query(StudentEnrolment).filter(
        StudentEnrolment.institution_id == institution_id,
        StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
    ).count()

    course_intakes = db.query(InstitutionCourseIntake).filter(
        InstitutionCourseIntake.institution_id == institution_id
    ).all()

    intake_outs = []
    has_over_admission = False
    for ci in course_intakes:
        course_title = ci.course.name if ci.course else "Unknown Course"
        programme_title = ci.programme.name if ci.programme else "Engineering & Technology"
        actual_regular = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == institution_id,
            StudentEnrolment.course_id == ci.course_id,
            StudentEnrolment.is_supernumerary == False,
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).count()

        actual_super = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == institution_id,
            StudentEnrolment.course_id == ci.course_id,
            StudentEnrolment.is_supernumerary == True,
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).count()

        is_over = actual_regular > ci.approved_intake
        if is_over:
            has_over_admission = True

        occ = round((actual_regular / ci.approved_intake * 100), 1) if ci.approved_intake > 0 else 0.0

        intake_outs.append(CourseIntakeOut(
            id=ci.id,
            institution_id=ci.institution_id,
            academic_year=ci.academic_year,
            programme=programme_title,
            course=course_title,
            approved_intake=ci.approved_intake,
            tfw_supernumerary_quota=ci.tfw_supernumerary_quota,
            nri_supernumerary_quota=ci.nri_supernumerary_quota,
            fn_supernumerary_quota=ci.fn_supernumerary_quota,
            status=ci.status,
            actual_enrolment=actual_regular,
            actual_supernumerary=actual_super,
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
        intakes=intake_outs
    )

@router.get("/{institution_id}/reconciliation")
def get_intake_reconciliation(
    institution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Core AICTE Intake vs Enrolment Reconciliation Report:
    Compares AICTE approved seats against actual enrolled students for every course,
    verifying supernumerary quotas (TFW, NRI, FN) separately from approved core intake.
    """
    enforce_institution_scope(current_user, institution_id)
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")

    intakes = db.query(InstitutionCourseIntake).filter(InstitutionCourseIntake.institution_id == institution_id).all()
    rows = []

    for ci in intakes:
        course_title = ci.course.name if ci.course else "Unknown Course"
        programme_title = ci.programme.name if ci.programme else "Engineering & Technology"

        # Regular students
        regular_enrolled = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == institution_id,
            StudentEnrolment.course_id == ci.course_id,
            StudentEnrolment.is_supernumerary == False,
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).count()

        # TFW supernumerary
        tfw_enrolled = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == institution_id,
            StudentEnrolment.course_id == ci.course_id,
            StudentEnrolment.supernumerary_type == "TFW",
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).count()

        # NRI supernumerary
        nri_enrolled = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == institution_id,
            StudentEnrolment.course_id == ci.course_id,
            StudentEnrolment.nri_status == True,
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).count()

        # FN supernumerary
        fn_enrolled = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == institution_id,
            StudentEnrolment.course_id == ci.course_id,
            StudentEnrolment.foreign_national_status == True,
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).count()

        variance = ci.approved_intake - regular_enrolled
        is_over = regular_enrolled > ci.approved_intake
        tfw_breached = tfw_enrolled > ci.tfw_supernumerary_quota

        status_text = "COMPLIANT"
        if is_over:
            status_text = "OVER_ADMISSION_VIOLATION"
        elif tfw_breached:
            status_text = "TFW_QUOTA_BREACH"

        rows.append({
            "course": course_title,
            "programme": programme_title,
            "approved_intake": ci.approved_intake,
            "regular_enrolled": regular_enrolled,
            "variance": variance,
            "is_over_admitted": is_over,
            "tfw_quota": ci.tfw_supernumerary_quota,
            "tfw_enrolled": tfw_enrolled,
            "nri_quota": ci.nri_supernumerary_quota,
            "nri_enrolled": nri_enrolled,
            "fn_quota": ci.fn_supernumerary_quota,
            "fn_enrolled": fn_enrolled,
            "total_students": regular_enrolled + tfw_enrolled + nri_enrolled + fn_enrolled,
            "compliance_status": status_text
        })

    return {
        "institution_id": inst.id,
        "institution_name": inst.name,
        "aicte_id": inst.aicte_permanent_id,
        "academic_year": inst.approval_session,
        "reconciliation_rows": rows
    }
