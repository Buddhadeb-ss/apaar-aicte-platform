import io
import csv
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response, status
from sqlalchemy.orm import Session
from ..deps import get_db, get_current_user, enforce_institution_scope
from ...database.models import (
    Institution, Course, Student, StudentEnrolment, SignedCredential,
    ConsentRecord, BulkUploadJob, ValidationIssue, AuditEvent, User, InstitutionIntake
)
from ...schemas.v1_schemas import (
    BulkUploadJobOut, BulkDryRunResult, BulkDryRunRowError,
    BulkCommitIn, BulkCommitSummary
)
from ...core.identifiers import (
    generate_uuid, normalize_identifier, validate_apaar_format,
    mask_apaar_id, hash_apaar_id
)
from ...core.security import generate_credential_signature

router = APIRouter(prefix="/upload-jobs", tags=["Bulk Upload Jobs & Processing"])

@router.get("", response_model=List[BulkUploadJobOut])
def list_upload_jobs(
    institution_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List bulk upload processing jobs."""
    query = db.query(BulkUploadJob)
    if current_user.role in ("INSTITUTION_ADMIN", "INSTITUTION_OPERATOR"):
        query = query.filter(BulkUploadJob.institution_id == current_user.institution_id)
    elif institution_id:
        query = query.filter(BulkUploadJob.institution_id == institution_id)

    jobs = query.order_by(BulkUploadJob.created_at.desc()).limit(50).all()
    return [
        BulkUploadJobOut(
            id=j.id,
            institution_id=j.institution_id,
            filename=j.filename,
            academic_year=j.academic_year,
            total_records=j.total_records,
            valid_records=j.valid_records,
            error_records=j.error_records,
            status=j.status,
            created_at=j.created_at.strftime("%Y-%m-%d %H:%M:%S")
        )
        for j in jobs
    ]

@router.post("", response_model=BulkUploadJobOut, status_code=status.HTTP_201_CREATED)
async def create_upload_job(
    file: UploadFile = File(...),
    academic_year: str = Form("2024-2025"),
    institution_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process CSV bulk student upload in an atomic transaction:
    - Parses rows.
    - Validates mandatory fields and APAAR 12-digit Verhoeff checksum.
    - Automatically accepts valid records into the central database.
    - Creates structured ValidationIssue records for malformed rows.
    """
    target_inst_id = current_user.institution_id if current_user.role in ("INSTITUTION_ADMIN", "INSTITUTION_OPERATOR") else institution_id
    if not target_inst_id:
        raise HTTPException(status_code=400, detail="Institution ID required.")

    enforce_institution_scope(current_user, target_inst_id)

    inst = db.query(Institution).filter(Institution.id == target_inst_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")

    contents = await file.read()
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = contents.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or malformed.")

    job_id = generate_uuid()
    job = BulkUploadJob(
        id=job_id,
        institution_id=target_inst_id,
        created_by_user_id=current_user.id,
        filename=file.filename or "upload.csv",
        academic_year=academic_year,
        total_records=0,
        valid_records=0,
        error_records=0,
        status="PROCESSING"
    )
    db.add(job)
    db.flush()

    total_count = 0
    valid_count = 0
    error_count = 0
    seen_rolls = set()

    # Pre-cache courses for fast lookup
    courses = {c.id: c for c in db.query(Course).all()}
    courses_by_name = {c.name.lower(): c for c in courses.values()}
    courses_by_code = {c.code.lower(): c for c in courses.values()}

    for row_idx, row in enumerate(reader, start=1):
        total_count += 1
        row_clean = {k.strip(): (v.strip() if v else "") for k, v in row.items() if k}

        roll = normalize_identifier(row_clean.get("internal_id") or row_clean.get("internal_student_id", ""))
        name = row_clean.get("student_name", "").strip()
        dob = row_clean.get("date_of_birth", "").strip()
        gender = row_clean.get("gender", "MALE").strip().upper()
        cat = row_clean.get("category", "GENERAL").strip().upper()
        course_input = row_clean.get("course", "").strip()
        raw_apaar = row_clean.get("apaar_id", "").strip()
        super_str = row_clean.get("is_supernumerary", "FALSE").strip().upper()
        is_super = super_str in ("TRUE", "1", "YES")
        super_type = row_clean.get("supernumerary_type", "NONE").strip().upper()
        nri_status = row_clean.get("nri_status", "FALSE").strip().upper() in ("TRUE", "1", "YES")
        fn_status = row_clean.get("foreign_national_status", "FALSE").strip().upper() in ("TRUE", "1", "YES")

        errors = []

        if not roll:
            errors.append(("internal_id", "MISSING_ROLL_NO", "Roll / internal ID is mandatory."))
        elif roll in seen_rolls:
            errors.append(("internal_id", "DUPLICATE_ROLL_BATCH", f"Roll No '{roll}' duplicated within this CSV."))
        else:
            seen_rolls.add(roll)
            # Check DB roll uniqueness in institution
            existing_db_roll = db.query(StudentEnrolment).filter(
                StudentEnrolment.institution_id == target_inst_id,
                StudentEnrolment.academic_year == academic_year,
                StudentEnrolment.internal_student_id == roll
            ).first()
            if existing_db_roll:
                errors.append(("internal_id", "DUPLICATE_ROLL_DB", f"Roll No '{roll}' already exists in institutional database."))

        if not name:
            errors.append(("student_name", "MISSING_NAME", "Student name is required."))
        if not dob:
            errors.append(("date_of_birth", "MISSING_DOB", "Date of birth is required."))

        # Course matching
        target_course = None
        if course_input in courses:
            target_course = courses[course_input]
        elif course_input.lower() in courses_by_code:
            target_course = courses_by_code[course_input.lower()]
        elif course_input.lower() in courses_by_name:
            target_course = courses_by_name[course_input.lower()]
        else:
            # Fallback to first course if reasonable or flag error
            first_c = next(iter(courses.values()), None)
            if first_c:
                target_course = first_c
            else:
                errors.append(("course", "INVALID_COURSE", f"Unrecognized course: '{course_input}'."))

        # APAAR validation
        is_valid_ap, clean_ap, ap_err = validate_apaar_format(raw_apaar)
        if not is_valid_ap:
            errors.append(("apaar_id", "INVALID_APAAR_FORMAT", ap_err or "Invalid APAAR checksum."))

        if errors:
            error_count += 1
            for f_name, e_code, e_msg in errors:
                r_id = "RULE_06_MISSING_MANDATORY_FIELD"
                if "APAAR" in e_code:
                    r_id = "RULE_02_MALFORMED_APAAR"
                elif "DUPLICATE" in e_code or "ROLL" in e_code:
                    r_id = "RULE_13_DUPLICATE_FILE_ROWS" if "CSV" in e_msg or "BATCH" in e_code else "RULE_05_DUPLICATE_INTERNAL_ID"
                elif "COURSE" in e_code:
                    r_id = "RULE_08_INCONSISTENT_PROGRAMME"

                issue = ValidationIssue(
                    job_id=job.id,
                    institution_id=target_inst_id,
                    row_number=row_idx,
                    rule_id=r_id,
                    field_name=f_name,
                    error_code=e_code,
                    error_message=e_msg,
                    suggested_remediation="Verify field values in the source CSV and re-stage through the upload wizard.",
                    severity="CRITICAL",
                    anomaly_score=25.0,
                    raw_data_json=json.dumps(row_clean),
                    resolution_status="NEW"
                )
                db.add(issue)
        else:
            # Valid row -> Insert immediately
            valid_count += 1
            ap_hash = hash_apaar_id(clean_ap)
            ap_mask = mask_apaar_id(clean_ap)

            # Check collision
            collision = db.query(StudentEnrolment).join(Student).filter(
                Student.apaar_hash == ap_hash,
                StudentEnrolment.institution_id != target_inst_id,
                StudentEnrolment.academic_year == academic_year,
                StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
            ).first()

            rec_status = "ACCEPTED"
            disc_reason = None
            if collision:
                rec_status = "FLAGGED_DISCREPANCY"
                disc_reason = f"Duplicate APAAR collision: Student enrolled at {collision.institution.name}."

            student_rec = db.query(Student).filter(Student.apaar_hash == ap_hash).first()
            if not student_rec:
                student_rec = Student(
                    id=generate_uuid(),
                    student_name=name,
                    date_of_birth=dob,
                    gender=gender,
                    category=cat,
                    apaar_id_encrypted=clean_ap,
                    apaar_hash=ap_hash,
                    apaar_masked=ap_mask
                )
                db.add(student_rec)
                db.flush()

            enrol_rec = StudentEnrolment(
                id=generate_uuid(),
                student_id=student_rec.id,
                internal_student_id=roll,
                institution_id=target_inst_id,
                course_id=target_course.id,
                academic_year=academic_year,
                admission_year=2024,
                admission_category="REGULAR",
                is_supernumerary=is_super,
                supernumerary_type=super_type,
                nri_status=nri_status,
                foreign_national_status=fn_status,
                admission_status="ENROLLED",
                record_status=rec_status,
                discrepancy_reason=disc_reason
            )
            db.add(enrol_rec)
            db.flush()

            vtoken = generate_uuid()
            sig = generate_credential_signature(vtoken, roll, ap_hash, target_inst_id)
            db.add(SignedCredential(
                id=generate_uuid(),
                student_id=student_rec.id,
                enrolment_id=enrol_rec.id,
                verification_token=vtoken,
                signature_algorithm="HMAC-SHA256",
                signature_value=sig
            ))
            db.add(ConsentRecord(
                id=generate_uuid(),
                student_id=student_rec.id,
                purpose="National Depository & Verification",
                status="GRANTED"
            ))

    job.total_records = total_count
    job.valid_records = valid_count
    job.error_records = error_count
    job.status = "COMPLETED" if error_count == 0 else "REQUIRES_RESOLUTION"

    audit = AuditEvent(
        institution_id=target_inst_id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        event_type="BULK_UPLOAD_PROCESSED",
        resource_type="BULK_UPLOAD_JOB",
        resource_id=job.id,
        details_json=f'{{"total": {total_count}, "valid": {valid_count}, "errors": {error_count}}}'
    )
    db.add(audit)
    db.commit()

    return BulkUploadJobOut(
        id=job.id,
        institution_id=job.institution_id,
        filename=job.filename,
        academic_year=job.academic_year,
        total_records=total_count,
        valid_records=valid_count,
        error_records=error_count,
        status=job.status,
        created_at=job.created_at.strftime("%Y-%m-%d %H:%M:%S")
    )

@router.get("/template")
def download_bulk_template():
    """Download official standardized CSV template with valid Verhoeff demo records."""
    headers = [
        "internal_id", "student_name", "date_of_birth", "gender", "category",
        "course", "programme", "admission_year", "academic_year", "apaar_id",
        "is_supernumerary", "supernumerary_type", "nri_status", "oci_status", "foreign_national_status"
    ]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    # 2 Compliant Sample Rows
    writer.writerow([
        "AIT-2024-CSE-201", "Rhea Sengupta", "2004-06-18", "FEMALE", "GENERAL",
        "Computer Science & Engineering", "ENGINEERING_AND_TECHNOLOGY", "2024", "2024-2025",
        "829104829202", "FALSE", "NONE", "FALSE", "FALSE", "FALSE"
    ])
    writer.writerow([
        "AIT-2024-CSE-202", "Harshavardhan Rao", "2004-02-14", "MALE", "OBC",
        "Computer Science & Engineering", "ENGINEERING_AND_TECHNOLOGY", "2024", "2024-2025",
        "829104829210", "TRUE", "TFW", "FALSE", "FALSE", "FALSE"
    ])
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aicte_student_bulk_template.csv"}
    )

@router.post("/validate", response_model=BulkDryRunResult)
def validate_bulk_rows_dry_run(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Dry-Run Server-Side Pre-Validation for Bulk Import Wizard:
    - Pre-validates mapped rows without committing to database.
    - Runs required-field and type checks.
    - Validates 12-digit APAAR format with Verhoeff checksum.
    - Checks batch-internal duplicate rolls and existing database collisions.
    - Evaluates approved course intake limits.
    - Returns preview rows, errors, and counts.
    """
    rows = payload.get("rows", [])
    academic_year = payload.get("academic_year", "2024-2025")
    inst_id = payload.get("institution_id") or current_user.institution_id
    if not inst_id:
        raise HTTPException(status_code=400, detail="Institution ID required.")

    enforce_institution_scope(current_user, inst_id)

    courses = {c.id: c for c in db.query(Course).all()}
    courses_by_name = {c.name.lower(): c for c in courses.values()}
    courses_by_code = {c.code.lower(): c for c in courses.values()}

    seen_batch_rolls = set()
    errors: List[BulkDryRunRowError] = []
    preview_rows: List[Dict[str, Any]] = []

    valid_count = 0
    invalid_count = 0
    duplicate_count = 0

    for idx, row in enumerate(rows, start=1):
        row_clean = {k.strip(): (str(v).strip() if v is not None else "") for k, v in row.items()}
        roll = normalize_identifier(row_clean.get("internal_id") or row_clean.get("internal_student_id", ""))
        name = row_clean.get("student_name", "").strip()
        dob = row_clean.get("date_of_birth", "").strip()
        course_in = row_clean.get("course", "").strip()
        apaar = row_clean.get("apaar_id", "").strip()
        is_super = row_clean.get("is_supernumerary", "FALSE").upper() in ("TRUE", "1", "YES")

        row_errors = []
        is_dup_collision = False

        if not roll:
            row_errors.append(BulkDryRunRowError(row_index=idx, field_name="internal_id", error_code="MISSING_FIELD", error_message="Internal Roll No is required."))
        elif roll in seen_batch_rolls:
            row_errors.append(BulkDryRunRowError(row_index=idx, field_name="internal_id", error_code="DUPLICATE_BATCH_ROLL", error_message=f"Duplicate roll '{roll}' within uploaded file."))
        else:
            seen_batch_rolls.add(roll)
            # Check DB collision
            if db.query(StudentEnrolment).filter(StudentEnrolment.institution_id == inst_id, StudentEnrolment.academic_year == academic_year, StudentEnrolment.internal_student_id == roll).first():
                row_errors.append(BulkDryRunRowError(row_index=idx, field_name="internal_id", error_code="EXISTING_ROLL", error_message=f"Roll '{roll}' is already registered in this institution."))

        if not name:
            row_errors.append(BulkDryRunRowError(row_index=idx, field_name="student_name", error_code="MISSING_FIELD", error_message="Student name is required."))

        if not dob:
            row_errors.append(BulkDryRunRowError(row_index=idx, field_name="date_of_birth", error_code="MISSING_FIELD", error_message="Date of birth is required."))

        target_course = courses.get(course_in) or courses_by_code.get(course_in.lower()) or courses_by_name.get(course_in.lower())
        if not target_course:
            row_errors.append(BulkDryRunRowError(row_index=idx, field_name="course", error_code="UNKNOWN_COURSE", error_message=f"Course '{course_in}' does not match any approved AICTE course."))

        is_valid_ap, clean_ap, ap_err = validate_apaar_format(apaar)
        if not is_valid_ap:
            row_errors.append(BulkDryRunRowError(row_index=idx, field_name="apaar_id", error_code="INVALID_APAAR_CHECKSUM", error_message=f"APAAR Validation Failed: {ap_err}"))
        else:
            ap_hash = hash_apaar_id(clean_ap)
            collision = db.query(StudentEnrolment).join(Student).filter(
                Student.apaar_hash == ap_hash,
                StudentEnrolment.institution_id != inst_id,
                StudentEnrolment.academic_year == academic_year,
                StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
            ).first()
            if collision:
                is_dup_collision = True
                duplicate_count += 1
                row_errors.append(BulkDryRunRowError(row_index=idx, field_name="apaar_id", error_code="CROSS_INSTITUTION_COLLISION", error_message=f"Duplicate APAAR collision: Student enrolled at '{collision.institution.name}'.", severity="WARNING"))

        # Intake check
        if target_course and not is_super:
            intake = db.query(InstitutionIntake).filter(InstitutionIntake.institution_id == inst_id, InstitutionIntake.course_id == target_course.id, InstitutionIntake.academic_year == academic_year).first()
            if intake:
                curr_reg = db.query(StudentEnrolment).filter(StudentEnrolment.institution_id == inst_id, StudentEnrolment.course_id == target_course.id, StudentEnrolment.academic_year == academic_year, StudentEnrolment.is_supernumerary == False, StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])).count()
                if curr_reg >= intake.approved_intake:
                    row_errors.append(BulkDryRunRowError(row_index=idx, field_name="course", error_code="INTAKE_LIMIT_EXCEEDED", error_message=f"Course capacity limit of {intake.approved_intake} reached.", severity="WARNING"))

        errors.extend(row_errors)

        has_critical = any(e.severity == "CRITICAL" for e in row_errors)
        if has_critical:
            invalid_count += 1
            row_status = "INVALID"
        elif is_dup_collision:
            row_status = "DUPLICATE_COLLISION"
            valid_count += 1
        else:
            valid_count += 1
            row_status = "VALID"

        if idx <= 15:
            preview_rows.append({
                **row_clean,
                "row_index": idx,
                "_status": row_status,
                "_errors": [e.error_message for e in row_errors]
            })

    return BulkDryRunResult(
        total_rows=len(rows),
        valid_rows_count=valid_count,
        invalid_rows_count=invalid_count,
        duplicate_rows_count=duplicate_count,
        preview_rows=preview_rows,
        errors=errors,
        can_commit=valid_count > 0
    )

@router.post("/commit", response_model=BulkCommitSummary)
def commit_bulk_import_job(
    commit_in: BulkCommitIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Explicit Confirmation & Atomic Commit of Bulk Import:
    - Accepts pre-validated or raw rows.
    - Transactionally inserts valid records into Central Registry.
    - Stages invalid or colliding records into ValidationIssues queue.
    - Generates tamper-evident HMAC signatures and consent records.
    - Logs statutory audit event.
    """
    inst_id = commit_in.institution_id or current_user.institution_id
    if not inst_id:
        raise HTTPException(status_code=400, detail="Institution ID required.")

    enforce_institution_scope(current_user, inst_id)

    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")

    courses = {c.id: c for c in db.query(Course).all()}
    courses_by_name = {c.name.lower(): c for c in courses.values()}
    courses_by_code = {c.code.lower(): c for c in courses.values()}

    job_id = generate_uuid()
    job = BulkUploadJob(
        id=job_id,
        institution_id=inst_id,
        created_by_user_id=current_user.id,
        filename=commit_in.filename or "bulk_import.csv",
        academic_year=commit_in.academic_year,
        total_records=len(commit_in.rows),
        valid_records=0,
        error_records=0,
        status="PROCESSING"
    )
    db.add(job)
    db.flush()

    total_count = len(commit_in.rows)
    accepted_count = 0
    rejected_count = 0
    duplicate_count = 0
    seen_rolls = set()

    for idx, row in enumerate(commit_in.rows, start=1):
        row_clean = {k.strip(): (str(v).strip() if v is not None else "") for k, v in row.items()}
        roll = normalize_identifier(row_clean.get("internal_id") or row_clean.get("internal_student_id", ""))
        name = row_clean.get("student_name", "").strip()
        dob = row_clean.get("date_of_birth", "").strip()
        gender = row_clean.get("gender", "MALE").strip().upper()
        cat = row_clean.get("category", "GENERAL").strip().upper()
        course_in = row_clean.get("course", "").strip()
        apaar = row_clean.get("apaar_id", "").strip()
        super_str = row_clean.get("is_supernumerary", "FALSE").strip().upper()
        is_super = super_str in ("TRUE", "1", "YES")
        super_type = row_clean.get("supernumerary_type", "NONE").strip().upper()
        nri_status = row_clean.get("nri_status", "FALSE").strip().upper() in ("TRUE", "1", "YES")
        oci_status = row_clean.get("oci_status", "FALSE").strip().upper() in ("TRUE", "1", "YES")
        fn_status = row_clean.get("foreign_national_status", "FALSE").strip().upper() in ("TRUE", "1", "YES")

        row_errors = []

        if not roll:
            row_errors.append(("internal_id", "MISSING_ROLL", "Roll number is required."))
        elif roll in seen_rolls:
            row_errors.append(("internal_id", "DUPLICATE_ROLL_BATCH", f"Roll '{roll}' is duplicated in this upload batch."))
        else:
            seen_rolls.add(roll)
            if db.query(StudentEnrolment).filter(StudentEnrolment.institution_id == inst_id, StudentEnrolment.academic_year == commit_in.academic_year, StudentEnrolment.internal_student_id == roll).first():
                row_errors.append(("internal_id", "EXISTING_ROLL_DB", f"Roll '{roll}' already exists in session {commit_in.academic_year}."))

        if not name:
            row_errors.append(("student_name", "MISSING_NAME", "Student full name is required."))
        if not dob:
            row_errors.append(("date_of_birth", "MISSING_DOB", "Date of birth is required."))

        target_course = courses.get(course_in) or courses_by_code.get(course_in.lower()) or courses_by_name.get(course_in.lower())
        if not target_course:
            row_errors.append(("course", "UNKNOWN_COURSE", f"Course '{course_in}' not recognized."))

        is_valid_ap, clean_ap, ap_err = validate_apaar_format(apaar)
        if not is_valid_ap:
            row_errors.append(("apaar_id", "INVALID_APAAR_CHECKSUM", f"APAAR Validation Failed: {ap_err}"))

        if row_errors:
            rejected_count += 1
            for f_name, e_code, e_msg in row_errors:
                r_id = "RULE_06_MISSING_MANDATORY_FIELD"
                if "APAAR" in e_code:
                    r_id = "RULE_02_MALFORMED_APAAR"
                elif "DUPLICATE" in e_code:
                    r_id = "RULE_13_DUPLICATE_FILE_ROWS"
                elif "ROLL" in e_code:
                    r_id = "RULE_05_DUPLICATE_INTERNAL_ID"
                elif "COURSE" in e_code:
                    r_id = "RULE_08_INCONSISTENT_PROGRAMME"

                db.add(ValidationIssue(
                    job_id=job.id,
                    institution_id=inst_id,
                    row_number=idx,
                    rule_id=r_id,
                    field_name=f_name,
                    error_code=e_code,
                    error_message=e_msg,
                    suggested_remediation="Correct errors and re-stage through the upload review queue.",
                    severity="CRITICAL",
                    anomaly_score=25.0,
                    raw_data_json=json.dumps(row_clean),
                    resolution_status="NEW"
                ))
            continue

        # Check multi-college collision
        ap_hash = hash_apaar_id(clean_ap)
        ap_mask = mask_apaar_id(clean_ap)

        collision = db.query(StudentEnrolment).join(Student).filter(
            Student.apaar_hash == ap_hash,
            StudentEnrolment.institution_id != inst_id,
            StudentEnrolment.academic_year == commit_in.academic_year,
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).first()

        rec_status = "ACCEPTED"
        disc_reason = None
        if collision:
            rec_status = "FLAGGED_DISCREPANCY"
            disc_reason = f"Duplicate APAAR collision: Student enrolled at '{collision.institution.name}' (Roll: {collision.internal_student_id})."
            duplicate_count += 1

        # Check intake capacity
        if not is_super:
            intake = db.query(InstitutionIntake).filter(InstitutionIntake.institution_id == inst_id, InstitutionIntake.course_id == target_course.id, InstitutionIntake.academic_year == commit_in.academic_year).first()
            if intake:
                curr_reg = db.query(StudentEnrolment).filter(StudentEnrolment.institution_id == inst_id, StudentEnrolment.course_id == target_course.id, StudentEnrolment.academic_year == commit_in.academic_year, StudentEnrolment.is_supernumerary == False, StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])).count()
                if curr_reg >= intake.approved_intake:
                    rec_status = "FLAGGED_DISCREPANCY"
                    disc_reason = f"Sanctioned intake limit exceeded: Course capacity is {intake.approved_intake}, current regular enrolment is {curr_reg}."

        # Insert student identity if not already present
        student_rec = db.query(Student).filter(Student.apaar_hash == ap_hash).first()
        if not student_rec:
            student_rec = Student(
                id=generate_uuid(),
                student_name=name,
                date_of_birth=dob,
                gender=gender,
                category=cat,
                apaar_id_encrypted=clean_ap,
                apaar_hash=ap_hash,
                apaar_masked=ap_mask
            )
            db.add(student_rec)
            db.flush()

        # Insert enrolment
        enrol_rec = StudentEnrolment(
            id=generate_uuid(),
            student_id=student_rec.id,
            internal_student_id=roll,
            institution_id=inst_id,
            course_id=target_course.id,
            academic_year=commit_in.academic_year,
            admission_year=2024,
            is_supernumerary=is_super,
            supernumerary_type=super_type,
            nri_status=nri_status,
            oci_status=oci_status,
            foreign_national_status=fn_status,
            admission_status="ENROLLED",
            record_status=rec_status,
            discrepancy_reason=disc_reason
        )
        db.add(enrol_rec)
        db.flush()

        # Issue Signed Credential
        vtoken = generate_uuid()
        sig = generate_credential_signature(vtoken, roll, ap_hash, inst_id)
        db.add(SignedCredential(
            id=generate_uuid(),
            student_id=student_rec.id,
            enrolment_id=enrol_rec.id,
            verification_token=vtoken,
            signature_algorithm="HMAC-SHA256",
            signature_value=sig
        ))
        db.add(ConsentRecord(
            id=generate_uuid(),
            student_id=student_rec.id,
            purpose="National Academic Depository & Verification",
            status="GRANTED"
        ))
        accepted_count += 1

    job.valid_records = accepted_count
    job.error_records = rejected_count
    job.status = "COMPLETED" if rejected_count == 0 else "REQUIRES_RESOLUTION"

    audit = AuditEvent(
        institution_id=inst_id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        event_type="BULK_IMPORT_COMMITTED",
        resource_type="BULK_UPLOAD_JOB",
        resource_id=job.id,
        details_json=f'{{"total": {total_count}, "accepted": {accepted_count}, "rejected": {rejected_count}, "duplicates": {duplicate_count}}}'
    )
    db.add(audit)
    db.commit()

    return BulkCommitSummary(
        job_id=job.id,
        filename=job.filename,
        academic_year=job.academic_year,
        total_records=total_count,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        duplicate_count=duplicate_count,
        status=job.status,
        message=f"Import complete: {accepted_count} confirmed into Central Registry, {rejected_count} staged for resolution."
    )

@router.get("/{id}/export-errors")
def export_job_errors_csv(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download official CSV error report for a specific bulk upload job."""
    job = db.query(BulkUploadJob).filter(BulkUploadJob.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Upload job not found.")

    enforce_institution_scope(current_user, job.institution_id)

    issues = db.query(ValidationIssue).filter(ValidationIssue.job_id == id).order_by(ValidationIssue.row_number.asc()).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Row Number", "Field Name", "Error Code", "Error Message", "Severity", "Raw Data", "Resolution Status"])
    for iss in issues:
        writer.writerow([
            iss.row_number,
            iss.field_name,
            iss.error_code,
            iss.error_message,
            iss.severity,
            iss.raw_data_json,
            iss.resolution_status
        ])

    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=Import_Errors_Job_{job.id[:8]}.csv"}
    )
