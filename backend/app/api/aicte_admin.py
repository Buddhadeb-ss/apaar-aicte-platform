from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from .deps import get_db, require_role
from ..database.models import User, Institution, InstitutionCourseIntake, Student, StudentEnrolment, AuditLog, VerificationLog
from ..schemas.schemas import NationalAnalytics, DuplicateApaarAlert

router = APIRouter(prefix="/aicte", tags=["AICTE National Regulatory Scrutiny"])

@router.get("/analytics", response_model=NationalAnalytics)
def get_national_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["AICTE_ADMIN"]))
):
    """
    Returns aggregated national statistics strictly separating approved intake limits
    from student enrolment numbers.
    """
    # 1. Total Approved Intake (aggregated from InstitutionCourseIntake)
    total_approved = db.query(func.coalesce(func.sum(InstitutionCourseIntake.approved_intake), 0)).scalar()

    # 2. Total Actual Enrolled Students (aggregated from accepted Student records)
    total_enrolled = db.query(StudentEnrolment).filter(
        StudentEnrolment.record_status.in_(["ACCEPTED", "FLAGGED_DISCREPANCY"]),
        StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
    ).count()

    # 3. Supernumerary breakdown
    total_supernumerary = db.query(StudentEnrolment).filter(
        StudentEnrolment.is_supernumerary == True,
        StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
    ).count()

    total_institutions = db.query(Institution).count()
    total_programmes = db.query(func.count(func.distinct(InstitutionCourseIntake.programme_id))).scalar()

    # 4. Over-admission detection: Check course by course
    # A violation occurs if regular enrolled students > approved_intake
    over_admission_count = 0
    all_intakes = db.query(InstitutionCourseIntake).all()
    for intake in all_intakes:
        regular_enrolled = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == intake.institution_id,
            StudentEnrolment.course_id == intake.course_id,
            StudentEnrolment.academic_year == intake.academic_year,
            StudentEnrolment.is_supernumerary == False,
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).count()
        if regular_enrolled > intake.approved_intake:
            over_admission_count += 1

    # 5. Duplicate APAAR detection across different institutions
    duplicate_student_ids = db.query(StudentEnrolment.student_id).group_by(
        StudentEnrolment.student_id
    ).having(func.count(func.distinct(StudentEnrolment.institution_id)) > 1).all()

    duplicate_apaar_count = len(duplicate_student_ids)

    # 6. Verifications performed
    total_verifications = db.query(VerificationLog).count()

    # 7. Recent audits
    recent_audits = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(8).all()
    audit_list = [
        {
            "id": a.id,
            "action": a.action,
            "role": a.role,
            "user_email": a.user_email,
            "institution_id": a.institution_id,
            "details": a.details,
            "timestamp": a.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }
        for a in recent_audits
    ]

    occupancy_rate = round((total_enrolled / total_approved * 100), 2) if total_approved > 0 else 0.0

    return NationalAnalytics(
        total_institutions=total_institutions,
        total_programmes=total_programmes or 1,
        total_approved_intake=total_approved,
        total_actual_enrolled=total_enrolled,
        total_supernumerary_enrolled=total_supernumerary,
        overall_occupancy_rate=occupancy_rate,
        over_admission_violations=over_admission_count,
        duplicate_apaar_violations=duplicate_apaar_count,
        total_verifications_performed=total_verifications,
        recent_audit_actions=audit_list
    )

@router.get("/institutions")
def list_institutions_compliance(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["AICTE_ADMIN"]))
):
    """
    List all AICTE institutions with calculated approved capacity vs confirmed enrolment.
    """
    institutions = db.query(Institution).all()
    results = []

    for inst in institutions:
        total_approved = db.query(func.coalesce(func.sum(InstitutionCourseIntake.approved_intake), 0)).filter(
            InstitutionCourseIntake.institution_id == inst.id
        ).scalar()

        total_enrolled = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == inst.id,
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).count()

        has_over_admission = False
        course_intakes = db.query(InstitutionCourseIntake).filter(InstitutionCourseIntake.institution_id == inst.id).all()
        for ci in course_intakes:
            enrolled = db.query(StudentEnrolment).filter(
                StudentEnrolment.institution_id == inst.id,
                StudentEnrolment.course_id == ci.course_id,
                StudentEnrolment.is_supernumerary == False,
                StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
            ).count()
            if enrolled > ci.approved_intake:
                has_over_admission = True
                break

        status_str = "NON_COMPLIANT_OVER_ADMISSION" if has_over_admission else "COMPLIANT"

        results.append({
            "id": inst.id,
            "aicte_permanent_id": inst.aicte_permanent_id,
            "name": inst.name,
            "state": inst.state,
            "district": inst.district,
            "institution_type": inst.institution_type,
            "approval_session": inst.approval_session,
            "total_approved_intake": total_approved,
            "total_enrolled": total_enrolled,
            "occupancy_rate": round((total_enrolled / total_approved * 100), 1) if total_approved > 0 else 0.0,
            "compliance_status": status_str,
            "intake_status": status_str,
            "intakes": []
        })

    return results

@router.get("/duplicates", response_model=List[DuplicateApaarAlert])
def get_duplicate_apaar_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["AICTE_ADMIN"]))
):
    """
    Scans Central Registry for multi-institution collision:
    Detects any APAAR ID enrolled concurrently in 2 or more institutions.
    """
    duplicate_student_ids = db.query(StudentEnrolment.student_id).group_by(
        StudentEnrolment.student_id
    ).having(func.count(func.distinct(StudentEnrolment.institution_id)) > 1).all()

    alerts = []
    for (sid,) in duplicate_student_ids:
        st = db.query(Student).filter(Student.id == sid).first()
        if not st:
            continue

        institutions = list({enr.institution.name for enr in st.enrolments if enr.institution})
        courses = list({f"{enr.institution.name}: {enr.course.name}" for enr in st.enrolments if enr.institution and enr.course})

        alerts.append(DuplicateApaarAlert(
            apaar_hash=st.apaar_hash,
            apaar_masked=st.apaar_masked,
            student_name=st.student_name,
            institutions_involved=institutions,
            courses_involved=courses,
            academic_year=st.academic_year,
            flag="CONCURRENT_ENROLMENT_DISCREPANCY"
        ))

    return alerts

@router.get("/audit-logs")
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["AICTE_ADMIN"])),
    limit: int = Query(50, ge=1, le=200)
):
    """Return immutable system audit log entries."""
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "institution_id": l.institution_id,
            "user_email": l.user_email,
            "role": l.role,
            "action": l.action,
            "details": l.details,
            "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }
        for l in logs
    ]
