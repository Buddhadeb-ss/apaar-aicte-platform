import uuid
import io
import base64
import qrcode
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from .deps import get_db, get_current_user, enforce_institution_scope
from ..database.models import User, Institution, InstitutionCourseIntake, Student, StudentEnrolment, Course, SignedCredential, AuditLog
from ..schemas.schemas import StudentOut, StudentCreate, StudentCredentialDetail
from ..core.security import generate_credential_signature
from ..core.apaar_validator import (
    validate_apaar_format,
    clean_apaar_id,
    mask_apaar_id,
    hash_apaar_id,
    simulate_apaar_gateway_lookup
)

router = APIRouter(prefix="/students", tags=["Student Data Registry & Credentials"])

def make_qr_base64(payload_text: str) -> str:
    """Generate a base64 encoded PNG data URI for a QR code."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(payload_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0a192f", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

@router.get("", response_model=List[StudentOut])
def list_students(
    institution_id: Optional[str] = None,
    course: Optional[str] = None,
    search: Optional[str] = None,
    record_status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search and filter student records.
    APAAR IDs are strictly returned in masked privacy format (e.g. •••• •••• 1098).
    """
    query = db.query(Student).join(StudentEnrolment, Student.id == StudentEnrolment.student_id).join(Course, StudentEnrolment.course_id == Course.id)

    if current_user.role in ("INSTITUTE_ADMIN", "INSTITUTION_ADMIN"):
        query = query.filter(StudentEnrolment.institution_id == current_user.institution_id)
    elif current_user.role in ("STUDENT", "STUDENT_VIEWER"):
        query = query.filter(
            StudentEnrolment.institution_id == current_user.institution_id,
            StudentEnrolment.internal_student_id == current_user.student_internal_id
        )
    elif current_user.role == "AICTE_ADMIN":
        if institution_id:
            query = query.filter(StudentEnrolment.institution_id == institution_id)

    if course:
        query = query.filter(or_(Course.name == course, Course.code == course, Course.id == course))
    if record_status:
        query = query.filter(StudentEnrolment.record_status == record_status)
    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Student.student_name.ilike(search_fmt),
                StudentEnrolment.internal_student_id.ilike(search_fmt),
                Student.apaar_masked.ilike(search_fmt)
            )
        )

    students = query.order_by(Student.created_at.desc()).limit(limit).all()
    return students

@router.post("", response_model=StudentOut)
def create_student_record(
    student_in: StudentCreate,
    institution_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Single student record onboarding.
    Validates APAAR checksum, verifies approved course intake cap,
    and automatically issues cryptographic credential token.
    """
    target_inst_id = institution_id if institution_id else current_user.institution_id
    if not target_inst_id:
        raise HTTPException(status_code=400, detail="Target institution ID must be specified.")

    enforce_institution_scope(current_user, target_inst_id)

    inst = db.query(Institution).filter(Institution.id == target_inst_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")

    # 1. Validate APAAR
    is_valid, clean_apaar, err_msg = validate_apaar_format(student_in.apaar_id)
    if not is_valid:
        raise HTTPException(status_code=422, detail=f"APAAR Validation Failed: {err_msg}")

    # 2. Check internal ID uniqueness within institution
    existing_roll = db.query(StudentEnrolment).filter(
        StudentEnrolment.institution_id == target_inst_id,
        StudentEnrolment.academic_year == student_in.academic_year,
        StudentEnrolment.internal_student_id == student_in.internal_id
    ).first()
    if existing_roll:
        raise HTTPException(status_code=400, detail=f"Roll number '{student_in.internal_id}' already registered for this session.")

    # Resolve Course
    course_obj = db.query(Course).filter(or_(Course.name == student_in.course, Course.code == student_in.course, Course.id == student_in.course)).first()
    if not course_obj:
        course_obj = db.query(Course).first()

    # 3. Check for multi-institution collision
    apaar_hash = hash_apaar_id(clean_apaar)
    apaar_mask = mask_apaar_id(clean_apaar)
    collision = db.query(StudentEnrolment).join(Student, StudentEnrolment.student_id == Student.id).filter(
        Student.apaar_hash == apaar_hash,
        StudentEnrolment.institution_id != target_inst_id,
        StudentEnrolment.academic_year == student_in.academic_year
    ).first()

    rec_status = "ACCEPTED"
    disc_reason = None
    if collision:
        rec_status = "FLAGGED_DISCREPANCY"
        disc_reason = f"Duplicate APAAR collision: Student already registered at '{collision.institution.name}' (Roll: {collision.internal_student_id})."

    # 4. Check course intake limit
    course_intake = db.query(InstitutionCourseIntake).filter(
        InstitutionCourseIntake.institution_id == target_inst_id,
        InstitutionCourseIntake.course_id == course_obj.id,
        InstitutionCourseIntake.academic_year == student_in.academic_year
    ).first()

    if course_intake and not student_in.is_supernumerary:
        current_enrolled = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == target_inst_id,
            StudentEnrolment.course_id == course_obj.id,
            StudentEnrolment.academic_year == student_in.academic_year,
            StudentEnrolment.is_supernumerary == False,
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).count()
        if current_enrolled >= course_intake.approved_intake:
            rec_status = "FLAGGED_DISCREPANCY"
            disc_reason = f"Approved intake cap exceeded: Course capacity is {course_intake.approved_intake}, current regular enrolment is {current_enrolled}."

    student_rec = db.query(Student).filter(Student.apaar_hash == apaar_hash).first()
    if not student_rec:
        student_rec = Student(
            id=str(uuid.uuid4()),
            student_name=student_in.student_name,
            date_of_birth=student_in.date_of_birth,
            gender=student_in.gender,
            category=student_in.category,
            apaar_id_encrypted=clean_apaar,
            apaar_hash=apaar_hash,
            apaar_masked=apaar_mask
        )
        db.add(student_rec)
        db.flush()

    enrolment = StudentEnrolment(
        id=str(uuid.uuid4()),
        student_id=student_rec.id,
        internal_student_id=student_in.internal_id,
        institution_id=target_inst_id,
        course_id=course_obj.id,
        academic_year=student_in.academic_year,
        admission_year=student_in.admission_year,
        is_supernumerary=student_in.is_supernumerary,
        supernumerary_type=student_in.supernumerary_type,
        nri_status=student_in.nri_status,
        oci_status=student_in.oci_status,
        foreign_national_status=student_in.foreign_national_status,
        admission_status=student_in.admission_status,
        record_status=rec_status,
        discrepancy_reason=disc_reason
    )
    db.add(enrolment)
    db.flush()

    verif_token = str(uuid.uuid4())
    sig = generate_credential_signature(verif_token, student_in.internal_id, apaar_hash, target_inst_id)
    cred = SignedCredential(
        student_id=student_rec.id,
        enrolment_id=enrolment.id,
        verification_token=verif_token,
        signature_algorithm="HMAC-SHA256",
        signature_value=sig
    )
    db.add(cred)

    # Audit log
    audit = AuditLog(
        institution_id=target_inst_id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        event_type="STUDENT_ONBOARDING",
        resource_type="STUDENT",
        resource_id=student_rec.id,
        details_json=f"Onboarded student '{student_in.student_name}' ({student_in.internal_id}) in course '{course_obj.name}'. Status: {rec_status}."
    )
    db.add(audit)
    db.commit()
    db.refresh(student_rec)
    return student_rec

@router.get("/{student_id}/credential", response_model=StudentCredentialDetail)
def get_student_credential(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve digital student credential with QR code and simulated gateway link.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student record not found.")

    if current_user.role in ("INSTITUTE_ADMIN", "INSTITUTION_ADMIN"):
        enforce_institution_scope(current_user, student.institution_id)
    elif current_user.role in ("STUDENT", "STUDENT_VIEWER"):
        if student.internal_id != current_user.student_internal_id:
            raise HTTPException(status_code=403, detail="Cannot access credential of another student.")

    # QR payload with tamper-evident payload
    qr_payload = f"AICTE-APAAR-PASS|{student.verification_token}|{student.credential_signature}|{student.internal_id}|{student.institution_id}"
    qr_b64 = make_qr_base64(qr_payload)

    # Simulated Gateway query
    sim_status = simulate_apaar_gateway_lookup(student.apaar_masked, student.student_name, student.date_of_birth)

    return StudentCredentialDetail(
        id=student.id,
        internal_id=student.internal_id,
        institution_id=student.institution_id,
        institution_name=student.institution_name,
        academic_year=student.academic_year,
        programme=student.programme,
        course=student.course,
        admission_year=student.admission_year,
        apaar_masked=student.apaar_masked,
        student_name=student.student_name,
        date_of_birth=student.date_of_birth,
        gender=student.gender,
        category=student.category,
        is_supernumerary=student.is_supernumerary,
        supernumerary_type=student.supernumerary_type,
        nri_status=student.nri_status,
        oci_status=student.oci_status,
        foreign_national_status=student.foreign_national_status,
        admission_status=student.admission_status,
        record_status=student.record_status,
        discrepancy_reason=student.discrepancy_reason,
        verification_token=student.verification_token,
        credential_signature=student.credential_signature,
        qr_payload=qr_payload,
        qr_code_base64=qr_b64,
        simulated_gateway_status=sim_status
    )
