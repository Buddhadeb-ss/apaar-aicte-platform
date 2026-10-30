from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..deps import get_db, get_current_user, require_role, enforce_institution_scope
from ...database.models import Institution, InstitutionIntake, StudentEnrolment, User
from ...schemas.v1_schemas import IntakeReconciliationReport, CourseReconciliationRow

router = APIRouter(prefix="/intakes", tags=["Intake Limits & Enrolment Reconciliation"])

@router.get("/reconciliation/{institution_id}", response_model=IntakeReconciliationReport)
def get_intake_reconciliation(
    institution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Core AICTE Statutory Reconciliation Schedule:
    Strictly separates approved core intake from individual student records,
    and audits supernumerary quotas (TFW, NRI, Foreign National) outside regular seats.
    """
    enforce_institution_scope(current_user, institution_id)
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")

    intakes = db.query(InstitutionIntake).filter(InstitutionIntake.institution_id == institution_id).all()
    rows: List[CourseReconciliationRow] = []

    for ci in intakes:
        # Regular confirmed students
        reg_enrolled = db.query(StudentEnrolment).filter(
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

        variance = ci.approved_intake - reg_enrolled
        is_over = reg_enrolled > ci.approved_intake
        tfw_breached = tfw_enrolled > ci.tfw_supernumerary_quota

        status_text = "COMPLIANT"
        if is_over:
            status_text = "OVER_ADMISSION_VIOLATION"
        elif tfw_breached:
            status_text = "TFW_QUOTA_BREACH"

        rows.append(CourseReconciliationRow(
            course_id=ci.course_id,
            course=ci.course.name if ci.course else "Unknown Course",
            programme=ci.programme.name if ci.programme else "Unknown Programme",
            approved_intake=ci.approved_intake,
            regular_enrolled=reg_enrolled,
            variance=variance,
            is_over_admitted=is_over,
            tfw_quota=ci.tfw_supernumerary_quota,
            tfw_enrolled=tfw_enrolled,
            nri_quota=ci.nri_supernumerary_quota,
            nri_enrolled=nri_enrolled,
            fn_quota=ci.fn_supernumerary_quota,
            fn_enrolled=fn_enrolled,
            total_students=reg_enrolled + tfw_enrolled + nri_enrolled + fn_enrolled,
            compliance_status=status_text
        ))

    return IntakeReconciliationReport(
        institution_id=inst.id,
        institution_name=inst.name,
        aicte_id=inst.aicte_permanent_id,
        academic_year=inst.approval_session,
        reconciliation_rows=rows
    )
