import io
import base64
import qrcode
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..deps import get_db, get_current_user, enforce_institution_scope
from ...database.models import (
    Student, StudentEnrolment, Institution, Course, InstitutionIntake,
    SignedCredential, ConsentRecord, AuditEvent, User, ValidationIssue
)
from ...schemas.v1_schemas import (
    StudentEnrolmentOut, StudentCreateIn, StudentUpdateIn,
    StudentCredentialPass, StudentHistoryItem, PaginatedResponse
)
from ...core.security import generate_credential_signature
from ...core.identifiers import (
    generate_uuid, normalize_identifier, validate_apaar_format,
    mask_apaar_id, hash_apaar_id
)
from ...core.apaar_validator import simulate_apaar_gateway_lookup

router = APIRouter(prefix="/students", tags=["Student Identity & Enrolment Registry"])

def make_qr_base64(payload_text: str) -> str:
    """Generate base64 encoded PNG data URI for verifiable QR code."""
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

@router.get("", response_model=PaginatedResponse[StudentEnrolmentOut])
def list_students(
    institution_id: Optional[str] = None,
    course_id: Optional[str] = None,
    programme_id: Optional[str] = None,
    academic_year: Optional[str] = None,
    admission_status: Optional[str] = None,
    search: Optional[str] = None,
    record_status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search and filter student enrolments with multi-dimensional criteria.
    APAAR IDs are strictly returned in privacy-masked format (•••• •••• XXXX).
    """
    query = db.query(StudentEnrolment).join(Student).join(Institution).join(Course)

    if current_user.role in ("INSTITUTION_ADMIN", "INSTITUTION_OPERATOR"):
        query = query.filter(StudentEnrolment.institution_id == current_user.institution_id)
    elif current_user.role == "STUDENT_VIEWER":
        query = query.filter(StudentEnrolment.student_id == current_user.student_id)
    elif current_user.role == "AICTE_ADMIN":
        if institution_id:
            query = query.filter(StudentEnrolment.institution_id == institution_id)

    if course_id:
        query = query.filter(StudentEnrolment.course_id == course_id)
    if programme_id:
        query = query.filter(Course.programme_id == programme_id)
    if academic_year:
        query = query.filter(StudentEnrolment.academic_year == academic_year)
    if admission_status:
        query = query.filter(StudentEnrolment.admission_status == admission_status)
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

    total = query.count()
    enrolments = query.order_by(StudentEnrolment.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    items = []
    for e in enrolments:
        # Retrieve primary credential signature and token
        cred = db.query(SignedCredential).filter(SignedCredential.enrolment_id == e.id).first()
        token = cred.verification_token if cred else generate_uuid()
        sig = cred.signature_value if cred else "SIG_UNAVAILABLE"

        items.append(StudentEnrolmentOut(
            id=e.id,
            student_id=e.student_id,
            internal_student_id=e.internal_student_id,
            institution_id=e.institution_id,
            institution_name=e.institution.name if e.institution else "Unknown",
            course_id=e.course_id,
            course_name=e.course.name if e.course else "Unknown",
            programme_name=e.course.programme.name if e.course and e.course.programme else "Unknown",
            academic_year=e.academic_year,
            admission_year=e.admission_year,
            apaar_masked=e.student.apaar_masked if e.student else "•••• •••• ••••",
            student_name=e.student.student_name if e.student else "Unknown",
            date_of_birth=e.student.date_of_birth if e.student else "2000-01-01",
            gender=e.student.gender if e.student else "MALE",
            category=e.student.category if e.student else "GENERAL",
            is_supernumerary=e.is_supernumerary,
            supernumerary_type=e.supernumerary_type,
            nri_status=e.nri_status,
            oci_status=e.oci_status,
            foreign_national_status=e.foreign_national_status,
            admission_status=e.admission_status,
            record_status=e.record_status,
            discrepancy_reason=e.discrepancy_reason,
            verification_token=token,
            credential_signature=sig
        ))

    total_pages = (total + limit - 1) // limit if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

@router.post("", response_model=StudentEnrolmentOut, status_code=status.HTTP_201_CREATED)
def create_student_enrolment(
    student_in: StudentCreateIn,
    institution_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Onboard student record in a single ACID transaction:
    - Normalizes internal roll ID.
    - Validates 12-digit APAAR format with Verhoeff checksum.
    - Checks duplicate roll number in session.
    - Checks collision across institutions.
    - Checks approved intake capacity.
    - Creates Student + StudentEnrolment + SignedCredential + ConsentRecord.
    """
    if current_user.role not in ("AICTE_ADMIN", "INSTITUTION_ADMIN", "INSTITUTION_OPERATOR", "INSTITUTE_ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Role '{current_user.role}' is not authorized to onboard student records."
        )

    target_inst_id = institution_id if institution_id else current_user.institution_id
    if not target_inst_id:
        raise HTTPException(status_code=400, detail="Target institution ID must be specified.")

    enforce_institution_scope(current_user, target_inst_id)

    inst = db.query(Institution).filter(Institution.id == target_inst_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")

    course = db.query(Course).filter(Course.id == student_in.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail=f"Course with ID '{student_in.course_id}' not found.")

    # 1. Validate APAAR
    is_valid_ap, clean_ap, ap_err = validate_apaar_format(student_in.apaar_id)
    if not is_valid_ap:
        raise HTTPException(status_code=422, detail=f"APAAR Validation Failed: {ap_err}")

    # 2. Normalize and check roll number
    norm_roll = normalize_identifier(student_in.internal_student_id)
    existing_enrol = db.query(StudentEnrolment).filter(
        StudentEnrolment.institution_id == target_inst_id,
        StudentEnrolment.academic_year == student_in.academic_year,
        StudentEnrolment.internal_student_id == norm_roll
    ).first()
    if existing_enrol:
        raise HTTPException(status_code=400, detail=f"Roll number '{norm_roll}' is already registered in this institution for session {student_in.academic_year}.")

    # 3. Detect duplicate collision across other institutions
    apaar_hash = hash_apaar_id(clean_ap)
    apaar_mask = mask_apaar_id(clean_ap)

    collision_enrol = db.query(StudentEnrolment).join(Student).filter(
        Student.apaar_hash == apaar_hash,
        StudentEnrolment.institution_id != target_inst_id,
        StudentEnrolment.academic_year == student_in.academic_year,
        StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
    ).first()

    rec_status = "ACCEPTED"
    disc_reason = None
    if collision_enrol:
        rec_status = "FLAGGED_DISCREPANCY"
        disc_reason = f"Duplicate APAAR Collision: Student concurrently enrolled at {collision_enrol.institution.name} (Roll: {collision_enrol.internal_student_id})."

    # 4. Check sanctioned intake limit
    intake = db.query(InstitutionIntake).filter(
        InstitutionIntake.institution_id == target_inst_id,
        InstitutionIntake.course_id == student_in.course_id,
        InstitutionIntake.academic_year == student_in.academic_year
    ).first()

    if intake and not student_in.is_supernumerary:
        current_reg = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == target_inst_id,
            StudentEnrolment.course_id == student_in.course_id,
            StudentEnrolment.academic_year == student_in.academic_year,
            StudentEnrolment.is_supernumerary == False,
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).count()
        if current_reg >= intake.approved_intake:
            rec_status = "FLAGGED_DISCREPANCY"
            disc_reason = f"Sanctioned intake limit exceeded: Course capacity is {intake.approved_intake}, current confirmed regular enrolment is {current_reg}."

    # 5. Transactional Insertion
    try:
        # Check if student identity already exists with this APAAR
        student_rec = db.query(Student).filter(Student.apaar_hash == apaar_hash).first()
        if not student_rec:
            student_rec = Student(
                id=generate_uuid(),
                student_name=student_in.student_name.strip(),
                date_of_birth=student_in.date_of_birth.strip(),
                gender=student_in.gender.upper(),
                category=student_in.category.upper(),
                apaar_id_encrypted=clean_ap,
                apaar_hash=apaar_hash,
                apaar_masked=apaar_mask
            )
            db.add(student_rec)
            db.flush()

        # Create Enrolment
        enrol_id = generate_uuid()
        enrol_rec = StudentEnrolment(
            id=enrol_id,
            student_id=student_rec.id,
            internal_student_id=norm_roll,
            institution_id=target_inst_id,
            course_id=student_in.course_id,
            academic_year=student_in.academic_year,
            admission_year=student_in.admission_year,
            is_supernumerary=student_in.is_supernumerary,
            supernumerary_type=student_in.supernumerary_type.upper(),
            nri_status=student_in.nri_status,
            oci_status=student_in.oci_status,
            foreign_national_status=student_in.foreign_national_status,
            admission_status="ENROLLED",
            record_status=rec_status,
            discrepancy_reason=disc_reason
        )
        db.add(enrol_rec)
        db.flush()

        # Create Signed Credential
        verif_token = generate_uuid()
        sig = generate_credential_signature(verif_token, norm_roll, apaar_hash, target_inst_id)
        cred_rec = SignedCredential(
            id=generate_uuid(),
            student_id=student_rec.id,
            enrolment_id=enrol_rec.id,
            verification_token=verif_token,
            signature_algorithm="HMAC-SHA256",
            signature_value=sig
        )
        db.add(cred_rec)

        # Create Consent Record
        consent_rec = ConsentRecord(
            id=generate_uuid(),
            student_id=student_rec.id,
            purpose="National Academic Depository & Verification",
            status="GRANTED"
        )
        db.add(consent_rec)

        # If record flagged for discrepancy, persist structured issue to Validation Workbench
        if rec_status == "FLAGGED_DISCREPANCY" and disc_reason:
            is_collision = "Duplicate APAAR" in disc_reason
            r_id = "RULE_04_CROSS_INST_DUPLICATE" if is_collision else "RULE_09_INTAKE_EXCEEDED"
            e_code = "CROSS_INSTITUTION_DUPLICATE" if is_collision else "ADMISSIONS_EXCEED_APPROVED_INTAKE"
            rem = "Initiate central AICTE scrutiny to resolve dual admission." if is_collision else "Halt regular admissions or seek approved intake expansion."
            db.add(ValidationIssue(
                institution_id=target_inst_id,
                student_id=student_rec.id,
                enrolment_id=enrol_id,
                rule_id=r_id,
                field_name="apaar_id" if is_collision else "course_id",
                error_code=e_code,
                error_message=disc_reason,
                suggested_remediation=rem,
                severity="HIGH" if is_collision else "CRITICAL",
                anomaly_score=40.0,
                resolution_status="NEW"
            ))

        # Log sanitized Audit Event (NO sensitive PII)
        audit = AuditEvent(
            institution_id=target_inst_id,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            event_type="STUDENT_ENROLLED",
            resource_type="STUDENT_ENROLMENT",
            resource_id=enrol_id,
            details_json=f'{{"roll_no": "{norm_roll}", "course_id": "{student_in.course_id}", "status": "{rec_status}"}}'
        )
        db.add(audit)
        db.commit()

        return StudentEnrolmentOut(
            id=enrol_rec.id,
            student_id=student_rec.id,
            internal_student_id=norm_roll,
            institution_id=target_inst_id,
            institution_name=inst.name,
            course_id=course.id,
            course_name=course.name,
            programme_name=course.programme.name if course.programme else "Unknown",
            academic_year=enrol_rec.academic_year,
            admission_year=enrol_rec.admission_year,
            apaar_masked=student_rec.apaar_masked,
            student_name=student_rec.student_name,
            date_of_birth=student_rec.date_of_birth,
            gender=student_rec.gender,
            category=student_rec.category,
            is_supernumerary=enrol_rec.is_supernumerary,
            supernumerary_type=enrol_rec.supernumerary_type,
            nri_status=enrol_rec.nri_status,
            oci_status=enrol_rec.oci_status,
            foreign_national_status=enrol_rec.foreign_national_status,
            admission_status=enrol_rec.admission_status,
            record_status=enrol_rec.record_status,
            discrepancy_reason=enrol_rec.discrepancy_reason,
            verification_token=verif_token,
            credential_signature=sig
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database transaction aborted: {str(exc)}")

@router.get("/{id}/credential", response_model=StudentCredentialPass)
def get_student_credential(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve digital student credential with QR code, HMAC server signature,
    and simulated DigiLocker/ABC gateway status.
    """
    enrol = db.query(StudentEnrolment).filter(
        or_(StudentEnrolment.id == id, StudentEnrolment.student_id == id)
    ).first()
    if not enrol:
        raise HTTPException(status_code=404, detail="Student enrolment record not found.")

    if current_user.role in ("INSTITUTION_ADMIN", "INSTITUTION_OPERATOR"):
        enforce_institution_scope(current_user, enrol.institution_id)
    elif current_user.role == "STUDENT_VIEWER":
        if enrol.student_id != current_user.student_id:
            raise HTTPException(status_code=403, detail="Access denied: Cannot access credential of another student.")

    cred = db.query(SignedCredential).filter(SignedCredential.enrolment_id == enrol.id).first()
    token = cred.verification_token if cred else generate_uuid()
    sig = cred.signature_value if cred else "SIG_UNAVAILABLE"

    qr_payload = f"AICTE-APAAR-PASS|{token}|{sig}|{enrol.internal_student_id}|{enrol.institution_id}"
    qr_b64 = make_qr_base64(qr_payload)

    sim_gateway = simulate_apaar_gateway_lookup(
        enrol.student.apaar_id_encrypted,
        enrol.student.student_name,
        enrol.student.date_of_birth
    )

    consent = db.query(ConsentRecord).filter(ConsentRecord.student_id == enrol.student_id).first()
    consent_status = consent.status if consent else "GRANTED"

    return StudentCredentialPass(
        id=enrol.id,
        student_id=enrol.student_id,
        internal_student_id=enrol.internal_student_id,
        institution_id=enrol.institution_id,
        institution_name=enrol.institution.name if enrol.institution else "Unknown",
        course_id=enrol.course_id,
        course_name=enrol.course.name if enrol.course else "Unknown",
        programme_name=enrol.course.programme.name if enrol.course and enrol.course.programme else "Unknown",
        academic_year=enrol.academic_year,
        admission_year=enrol.admission_year,
        apaar_masked=enrol.student.apaar_masked,
        student_name=enrol.student.student_name,
        date_of_birth=enrol.student.date_of_birth,
        gender=enrol.student.gender,
        category=enrol.student.category,
        is_supernumerary=enrol.is_supernumerary,
        supernumerary_type=enrol.supernumerary_type,
        nri_status=enrol.nri_status,
        oci_status=enrol.oci_status,
        foreign_national_status=enrol.foreign_national_status,
        admission_status=enrol.admission_status,
        record_status=enrol.record_status,
        discrepancy_reason=enrol.discrepancy_reason,
        verification_token=token,
        credential_signature=sig,
        qr_payload=qr_payload,
        qr_code_base64=qr_b64,
        simulated_gateway_status=sim_gateway,
        consent_status=consent_status
    )

@router.get("/{id}", response_model=StudentEnrolmentOut)
def get_student_detail(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve detailed student enrolment record with institution scoping."""
    enrol = db.query(StudentEnrolment).filter(
        or_(StudentEnrolment.id == id, StudentEnrolment.student_id == id)
    ).first()
    if not enrol:
        raise HTTPException(status_code=404, detail="Student enrolment record not found.")

    if current_user.role in ("INSTITUTION_ADMIN", "INSTITUTION_OPERATOR"):
        enforce_institution_scope(current_user, enrol.institution_id)
    elif current_user.role == "STUDENT_VIEWER":
        if enrol.student_id != current_user.student_id:
            raise HTTPException(status_code=403, detail="Access denied: Cannot access another student.")

    cred = db.query(SignedCredential).filter(SignedCredential.enrolment_id == enrol.id).first()
    token = cred.verification_token if cred else generate_uuid()
    sig = cred.signature_value if cred else "SIG_UNAVAILABLE"

    return StudentEnrolmentOut(
        id=enrol.id,
        student_id=enrol.student_id,
        internal_student_id=enrol.internal_student_id,
        institution_id=enrol.institution_id,
        institution_name=enrol.institution.name if enrol.institution else "Unknown",
        course_id=enrol.course_id,
        course_name=enrol.course.name if enrol.course else "Unknown",
        programme_name=enrol.course.programme.name if enrol.course and enrol.course.programme else "Unknown",
        academic_year=enrol.academic_year,
        admission_year=enrol.admission_year,
        apaar_masked=enrol.student.apaar_masked,
        student_name=enrol.student.student_name,
        date_of_birth=enrol.student.date_of_birth,
        gender=enrol.student.gender,
        category=enrol.student.category,
        is_supernumerary=enrol.is_supernumerary,
        supernumerary_type=enrol.supernumerary_type,
        nri_status=enrol.nri_status,
        oci_status=enrol.oci_status,
        foreign_national_status=enrol.foreign_national_status,
        admission_status=enrol.admission_status,
        record_status=enrol.record_status,
        discrepancy_reason=enrol.discrepancy_reason,
        verification_token=token,
        credential_signature=sig
    )

@router.put("/{id}", response_model=StudentEnrolmentOut)
def update_student_record(
    id: str,
    update_in: StudentUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update student record with server-side validation and audit logging:
    - Enforces institution ownership.
    - Re-validates APAAR format if updated.
    - Enforces uniqueness constraints on internal roll number.
    - Detects duplicate APAAR collisions across institutions.
    - Checks sanctioned intake limit capacity.
    - Creates immutable AuditEvent.
    """
    if current_user.role not in ("AICTE_ADMIN", "INSTITUTION_ADMIN", "INSTITUTION_OPERATOR", "INSTITUTE_ADMIN"):
        raise HTTPException(status_code=403, detail="Unauthorized: Role is not permitted to edit student records.")

    enrol = db.query(StudentEnrolment).filter(
        or_(StudentEnrolment.id == id, StudentEnrolment.student_id == id)
    ).first()
    if not enrol:
        raise HTTPException(status_code=404, detail="Student enrolment record not found.")

    enforce_institution_scope(current_user, enrol.institution_id)

    student = enrol.student
    if not student:
        raise HTTPException(status_code=404, detail="Student identity record not found.")

    course = db.query(Course).filter(Course.id == update_in.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail=f"Course with ID '{update_in.course_id}' not found.")

    norm_roll = normalize_identifier(update_in.internal_student_id)

    # Check roll number uniqueness within this institution and session
    existing_roll = db.query(StudentEnrolment).filter(
        StudentEnrolment.institution_id == enrol.institution_id,
        StudentEnrolment.academic_year == update_in.academic_year,
        StudentEnrolment.internal_student_id == norm_roll,
        StudentEnrolment.id != enrol.id
    ).first()
    if existing_roll:
        raise HTTPException(
            status_code=400,
            detail=f"Roll number '{norm_roll}' is already in use by another student in session {update_in.academic_year}."
        )

    apaar_hash = student.apaar_hash
    # If APAAR ID is supplied and changed
    if update_in.apaar_id and update_in.apaar_id.strip():
        is_valid_ap, clean_ap, ap_err = validate_apaar_format(update_in.apaar_id)
        if not is_valid_ap:
            raise HTTPException(status_code=422, detail=f"APAAR Validation Failed: {ap_err}")
        apaar_hash = hash_apaar_id(clean_ap)
        student.apaar_id_encrypted = clean_ap
        student.apaar_hash = apaar_hash
        student.apaar_masked = mask_apaar_id(clean_ap)

    # Detect duplicate collision across other institutions
    collision = db.query(StudentEnrolment).join(Student).filter(
        Student.apaar_hash == apaar_hash,
        StudentEnrolment.institution_id != enrol.institution_id,
        StudentEnrolment.academic_year == update_in.academic_year,
        StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
    ).first()

    rec_status = "ACCEPTED"
    disc_reason = None
    if collision:
        rec_status = "FLAGGED_DISCREPANCY"
        disc_reason = f"Duplicate APAAR Collision: Student concurrently enrolled at {collision.institution.name} (Roll: {collision.internal_student_id})."

    # Check sanctioned intake limit if course, session, or supernumerary status changed
    intake = db.query(InstitutionIntake).filter(
        InstitutionIntake.institution_id == enrol.institution_id,
        InstitutionIntake.course_id == update_in.course_id,
        InstitutionIntake.academic_year == update_in.academic_year
    ).first()

    if intake and not update_in.is_supernumerary and update_in.admission_status in ("ENROLLED", "ADMITTED"):
        current_reg = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == enrol.institution_id,
            StudentEnrolment.course_id == update_in.course_id,
            StudentEnrolment.academic_year == update_in.academic_year,
            StudentEnrolment.is_supernumerary == False,
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"]),
            StudentEnrolment.id != enrol.id
        ).count()
        if current_reg >= intake.approved_intake:
            rec_status = "FLAGGED_DISCREPANCY"
            disc_reason = f"Sanctioned intake limit exceeded: Course capacity is {intake.approved_intake}, current confirmed regular enrolment is {current_reg}."

    # Update Student Identity
    student.student_name = update_in.student_name.strip()
    student.date_of_birth = update_in.date_of_birth.strip()
    student.gender = update_in.gender.upper()
    student.category = update_in.category.upper()

    # Update Enrolment
    enrol.internal_student_id = norm_roll
    enrol.course_id = update_in.course_id
    enrol.academic_year = update_in.academic_year
    enrol.admission_year = update_in.admission_year
    enrol.admission_status = update_in.admission_status.upper()
    enrol.is_supernumerary = update_in.is_supernumerary
    enrol.supernumerary_type = update_in.supernumerary_type.upper()
    enrol.nri_status = update_in.nri_status
    enrol.oci_status = update_in.oci_status
    enrol.foreign_national_status = update_in.foreign_national_status
    enrol.record_status = rec_status
    enrol.discrepancy_reason = disc_reason

    # Re-sign credential
    cred = db.query(SignedCredential).filter(SignedCredential.enrolment_id == enrol.id).first()
    if not cred:
        verif_token = generate_uuid()
        sig = generate_credential_signature(verif_token, norm_roll, apaar_hash, enrol.institution_id)
        cred = SignedCredential(
            id=generate_uuid(),
            student_id=student.id,
            enrolment_id=enrol.id,
            verification_token=verif_token,
            signature_algorithm="HMAC-SHA256",
            signature_value=sig
        )
        db.add(cred)
    else:
        cred.signature_value = generate_credential_signature(
            cred.verification_token, norm_roll, apaar_hash, enrol.institution_id
        )

    # If record flagged for discrepancy, persist structured issue to Validation Workbench
    if rec_status == "FLAGGED_DISCREPANCY" and disc_reason:
        is_collision = "Duplicate APAAR" in disc_reason
        r_id = "RULE_04_CROSS_INST_DUPLICATE" if is_collision else "RULE_09_INTAKE_EXCEEDED"
        e_code = "CROSS_INSTITUTION_DUPLICATE" if is_collision else "ADMISSIONS_EXCEED_APPROVED_INTAKE"
        rem = "Initiate central AICTE scrutiny to resolve dual admission." if is_collision else "Halt regular admissions or seek approved intake expansion."
        db.add(ValidationIssue(
            institution_id=enrol.institution_id,
            student_id=student.id,
            enrolment_id=enrol.id,
            rule_id=r_id,
            field_name="apaar_id" if is_collision else "course_id",
            error_code=e_code,
            error_message=disc_reason,
            suggested_remediation=rem,
            severity="HIGH" if is_collision else "CRITICAL",
            anomaly_score=40.0,
            resolution_status="NEW"
        ))

    # Log sanitized Audit Event
    audit = AuditEvent(
        institution_id=enrol.institution_id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        event_type="STUDENT_UPDATED",
        resource_type="STUDENT_ENROLMENT",
        resource_id=enrol.id,
        details_json=f'{{"roll_no": "{norm_roll}", "course_id": "{update_in.course_id}", "status": "{rec_status}"}}'
    )
    db.add(audit)
    db.commit()

    return StudentEnrolmentOut(
        id=enrol.id,
        student_id=student.id,
        internal_student_id=enrol.internal_student_id,
        institution_id=enrol.institution_id,
        institution_name=enrol.institution.name if enrol.institution else "Unknown",
        course_id=course.id,
        course_name=course.name,
        programme_name=course.programme.name if course.programme else "Unknown",
        academic_year=enrol.academic_year,
        admission_year=enrol.admission_year,
        apaar_masked=student.apaar_masked,
        student_name=student.student_name,
        date_of_birth=student.date_of_birth,
        gender=student.gender,
        category=student.category,
        is_supernumerary=enrol.is_supernumerary,
        supernumerary_type=enrol.supernumerary_type,
        nri_status=enrol.nri_status,
        oci_status=enrol.oci_status,
        foreign_national_status=enrol.foreign_national_status,
        admission_status=enrol.admission_status,
        record_status=enrol.record_status,
        discrepancy_reason=enrol.discrepancy_reason,
        verification_token=cred.verification_token,
        credential_signature=cred.signature_value
    )

@router.get("/{id}/history", response_model=List[StudentHistoryItem])
def get_student_history(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve audit history trail for this student record."""
    enrol = db.query(StudentEnrolment).filter(
        or_(StudentEnrolment.id == id, StudentEnrolment.student_id == id)
    ).first()
    if not enrol:
        raise HTTPException(status_code=404, detail="Student record not found.")

    if current_user.role in ("INSTITUTION_ADMIN", "INSTITUTION_OPERATOR"):
        enforce_institution_scope(current_user, enrol.institution_id)

    events = db.query(AuditEvent).filter(
        or_(
            AuditEvent.resource_id == enrol.id,
            AuditEvent.resource_id == enrol.student_id
        )
    ).order_by(AuditEvent.timestamp.desc()).all()

    return [
        StudentHistoryItem(
            id=ev.id,
            event_type=ev.event_type,
            actor_email=ev.actor_email,
            actor_role=ev.actor_role,
            timestamp=ev.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            details=ev.details_json
        )
        for ev in events
    ]
