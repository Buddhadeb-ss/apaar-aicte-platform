import io
import csv
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response, status
from sqlalchemy.orm import Session
from .deps import get_db, get_current_user, enforce_institution_scope
from ..database.models import User, Institution, InstitutionCourseIntake, Student, ImportBatch, AuditLog
from ..schemas.schemas import ImportBatchResult, ResolveBatchRequest
from ..core.security import generate_credential_signature
from ..core.apaar_validator import (
    validate_apaar_format,
    clean_apaar_id,
    mask_apaar_id,
    hash_apaar_id
)

router = APIRouter(prefix="/import", tags=["Bulk Import & Error Resolution Workflow"])

CSV_HEADER = [
    "internal_id",
    "student_name",
    "date_of_birth",
    "gender",
    "category",
    "programme",
    "course",
    "admission_year",
    "academic_year",
    "apaar_id",
    "is_supernumerary",
    "supernumerary_type",
    "nri_status",
    "oci_status",
    "foreign_national_status"
]

@router.get("/template")
def download_csv_template():
    """Download official standardized CSV template for student onboarding."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADER)
    # Add two compliant example rows (with valid Verhoeff-checksummed APAARs)
    writer.writerow([
        "AIT-2024-CSE-101",
        "Vikrant Singhania",
        "2004-04-12",
        "MALE",
        "GENERAL",
        "ENGINEERING_AND_TECHNOLOGY",
        "Computer Science & Engineering",
        "2024",
        "2024-2025",
        "829104829202",
        "FALSE",
        "NONE",
        "FALSE",
        "FALSE",
        "FALSE"
    ])
    writer.writerow([
        "AIT-2024-CSE-102",
        "Pooja Deshmukh",
        "2004-09-28",
        "FEMALE",
        "OBC",
        "ENGINEERING_AND_TECHNOLOGY",
        "Computer Science & Engineering",
        "2024",
        "2024-2025",
        "829104829210",
        "TRUE",
        "TFW",
        "FALSE",
        "FALSE",
        "FALSE"
    ])
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aicte_student_import_template.csv"}
    )

@router.post("/upload", response_model=ImportBatchResult)
async def upload_student_csv(
    file: UploadFile = File(...),
    academic_year: str = Form("2024-2025"),
    institution_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process CSV bulk student upload:
    - Validates mandatory fields and APAAR 12-digit checksum.
    - Valid rows are immediately inserted into central registry.
    - Malformed or invalid rows are staged into an inline resolution queue.
    """
    target_inst_id = current_user.institution_id if current_user.role == "INSTITUTE_ADMIN" else institution_id
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
        raise HTTPException(status_code=400, detail="Empty or invalid CSV file.")

    batch_id = str(uuid.uuid4())
    total_rows = 0
    valid_count = 0
    error_rows = []

    seen_rolls_in_batch = set()

    for idx, row in enumerate(reader, start=1):
        total_rows += 1
        row_clean = {k.strip(): (v.strip() if v else "") for k, v in row.items() if k}

        internal_id = row_clean.get("internal_id", "")
        name = row_clean.get("student_name", "")
        dob = row_clean.get("date_of_birth", "")
        gender = row_clean.get("gender", "MALE").upper()
        cat = row_clean.get("category", "GENERAL").upper()
        prog = row_clean.get("programme", "ENGINEERING_AND_TECHNOLOGY")
        crse = row_clean.get("course", "")
        adm_year_str = row_clean.get("admission_year", "2024")
        raw_apaar = row_clean.get("apaar_id", "")
        is_super_str = row_clean.get("is_supernumerary", "FALSE").upper()
        is_super = is_super_str in ("TRUE", "1", "YES")
        super_type = row_clean.get("supernumerary_type", "NONE").upper()
        nri_status = row_clean.get("nri_status", "FALSE").upper() in ("TRUE", "1", "YES")
        oci_status = row_clean.get("oci_status", "FALSE").upper() in ("TRUE", "1", "YES")
        fn_status = row_clean.get("foreign_national_status", "FALSE").upper() in ("TRUE", "1", "YES")

        errors_in_row = []

        if not internal_id:
            errors_in_row.append("Missing internal_id / Roll No.")
        elif internal_id in seen_rolls_in_batch:
            errors_in_row.append(f"Duplicate Roll No '{internal_id}' repeated within this CSV file.")
        else:
            seen_rolls_in_batch.add(internal_id)

        if not name:
            errors_in_row.append("Missing student_name.")
        if not dob:
            errors_in_row.append("Missing date_of_birth.")
        if not crse:
            errors_in_row.append("Missing course.")

        # Validate APAAR
        is_valid_apaar, clean_apaar, apaar_err = validate_apaar_format(raw_apaar)
        if not is_valid_apaar:
            errors_in_row.append(f"APAAR error: {apaar_err}")

        # Check existing roll in database
        if internal_id:
            db_roll = db.query(Student).filter(
                Student.institution_id == target_inst_id,
                Student.academic_year == academic_year,
                Student.internal_id == internal_id
            ).first()
            if db_roll:
                errors_in_row.append(f"Roll No '{internal_id}' already exists in institutional database.")

        if errors_in_row:
            error_rows.append({
                "row_index": idx,
                "internal_id": internal_id,
                "student_name": name,
                "date_of_birth": dob,
                "course": crse,
                "programme": prog,
                "apaar_id": raw_apaar,
                "errors": errors_in_row,
                "category": cat,
                "supernumerary_type": super_type
            })
        else:
            # Valid row -> Insert immediately
            apaar_hash = hash_apaar_id(clean_apaar)
            apaar_mask = mask_apaar_id(clean_apaar)
            verif_token = str(uuid.uuid4())
            sig = generate_credential_signature(verif_token, internal_id, apaar_hash, target_inst_id)

            # Check duplicate collision across other institutions
            collision = db.query(Student).filter(
                Student.apaar_hash == apaar_hash,
                Student.institution_id != target_inst_id,
                Student.academic_year == academic_year
            ).first()

            rec_status = "ACCEPTED"
            disc_reason = None
            if collision:
                rec_status = "FLAGGED_DISCREPANCY"
                disc_reason = f"Duplicate APAAR: Student concurrently enrolled at {collision.institution_name}."

            st = Student(
                id=str(uuid.uuid4()),
                internal_id=internal_id,
                institution_id=target_inst_id,
                institution_name=inst.name,
                academic_year=academic_year,
                programme=prog,
                course=crse,
                admission_year=int(adm_year_str) if adm_year_str.isdigit() else 2024,
                apaar_id_raw=clean_apaar,
                apaar_hash=apaar_hash,
                apaar_masked=apaar_mask,
                student_name=name,
                date_of_birth=dob,
                gender=gender,
                category=cat,
                is_supernumerary=is_super,
                supernumerary_type=super_type,
                nri_status=nri_status,
                oci_status=oci_status,
                foreign_national_status=fn_status,
                admission_status="ENROLLED",
                record_status=rec_status,
                discrepancy_reason=disc_reason,
                verification_token=verif_token,
                credential_signature=sig
            )
            db.add(st)
            valid_count += 1

    batch_status = "COMPLETED" if len(error_rows) == 0 else "RESOLVING_ERRORS"
    batch_record = ImportBatch(
        id=batch_id,
        institution_id=target_inst_id,
        filename=file.filename or "upload.csv",
        academic_year=academic_year,
        total_rows=total_rows,
        valid_rows=valid_count,
        error_rows=len(error_rows),
        status=batch_status,
        staged_errors_json=json.dumps(error_rows)
    )
    db.add(batch_record)

    audit = AuditLog(
        institution_id=target_inst_id,
        user_email=current_user.email,
        role=current_user.role,
        action="CSV_IMPORT_PROCESSED",
        details=f"Uploaded '{file.filename}': {valid_count} accepted records, {len(error_rows)} flagged for error resolution."
    )
    db.add(audit)
    db.commit()

    return ImportBatchResult(
        batch_id=batch_id,
        filename=file.filename or "upload.csv",
        total_rows=total_rows,
        valid_rows=valid_count,
        error_rows=len(error_rows),
        status=batch_status,
        staged_errors=error_rows
    )

@router.post("/resolve")
def resolve_staged_import_errors(
    req: ResolveBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Inline Error Resolution Queue:
    Allows administrator to fix invalid rows (e.g. correct malformed APAAR or typo)
    without discarding the rest of the batch.
    """
    batch = db.query(ImportBatch).filter(ImportBatch.id == req.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch record not found.")

    enforce_institution_scope(current_user, batch.institution_id)
    inst = db.query(Institution).filter(Institution.id == batch.institution_id).first()

    staged_list = json.loads(batch.staged_errors_json or "[]")
    resolved_indices = set()
    newly_added = 0
    remaining_errors = []

    for item in req.resolved_rows:
        # Validate fixed APAAR
        is_valid, clean_apaar, err = validate_apaar_format(item.apaar_id)
        if not is_valid:
            raise HTTPException(status_code=422, detail=f"Row {item.row_index} still has invalid APAAR: {err}")

        # Check roll
        existing = db.query(Student).filter(
            Student.institution_id == batch.institution_id,
            Student.academic_year == batch.academic_year,
            Student.internal_id == item.internal_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Roll number '{item.internal_id}' already registered in institution.")

        apaar_hash = hash_apaar_id(clean_apaar)
        apaar_mask = mask_apaar_id(clean_apaar)
        verif_token = str(uuid.uuid4())
        sig = generate_credential_signature(verif_token, item.internal_id, apaar_hash, batch.institution_id)

        st = Student(
            id=str(uuid.uuid4()),
            internal_id=item.internal_id,
            institution_id=batch.institution_id,
            institution_name=inst.name,
            academic_year=batch.academic_year,
            programme="ENGINEERING_AND_TECHNOLOGY",
            course=item.course,
            admission_year=2024,
            apaar_id_raw=clean_apaar,
            apaar_hash=apaar_hash,
            apaar_masked=apaar_mask,
            student_name=item.student_name,
            date_of_birth=item.date_of_birth,
            gender="MALE",
            category=item.category,
            is_supernumerary=(item.supernumerary_type != "NONE"),
            supernumerary_type=item.supernumerary_type,
            admission_status="ENROLLED",
            record_status="ACCEPTED",
            verification_token=verif_token,
            credential_signature=sig
        )
        db.add(st)
        resolved_indices.add(item.row_index)
        newly_added += 1

    # Keep only unresolved staged errors
    for staged in staged_list:
        if staged.get("row_index") not in resolved_indices:
            remaining_errors.append(staged)

    batch.valid_rows += newly_added
    batch.error_rows = len(remaining_errors)
    batch.staged_errors_json = json.dumps(remaining_errors)
    batch.status = "COMPLETED" if len(remaining_errors) == 0 else "RESOLVING_ERRORS"

    audit = AuditLog(
        institution_id=batch.institution_id,
        user_email=current_user.email,
        role=current_user.role,
        action="IMPORT_ERRORS_RESOLVED",
        details=f"Resolved {newly_added} staged rows for batch {batch.id}. Remaining errors: {len(remaining_errors)}."
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "batch_status": batch.status,
        "resolved_count": newly_added,
        "remaining_error_count": len(remaining_errors),
        "remaining_errors": remaining_errors
    }

@router.get("/export-students")
def export_students_csv(
    institution_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export accepted students as CSV with masked APAAR IDs for data privacy.
    """
    target_inst_id = current_user.institution_id if current_user.role == "INSTITUTE_ADMIN" else institution_id
    if not target_inst_id and current_user.role != "AICTE_ADMIN":
        raise HTTPException(status_code=400, detail="Institution ID required.")

    query = db.query(Student)
    if target_inst_id:
        enforce_institution_scope(current_user, target_inst_id)
        query = query.filter(Student.institution_id == target_inst_id)

    students = query.order_by(Student.course, Student.internal_id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Institution ID", "Institution Name", "Roll No", "Student Name",
        "Date of Birth", "Gender", "Category", "Course", "Academic Year",
        "Masked APAAR ID", "Supernumerary", "Supernumerary Type", "Record Status"
    ])

    for s in students:
        writer.writerow([
            s.institution_id, s.institution_name, s.internal_id, s.student_name,
            s.date_of_birth, s.gender, s.category, s.course, s.academic_year,
            s.apaar_masked, s.is_supernumerary, s.supernumerary_type, s.record_status
        ])

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aicte_student_registry_export.csv"}
    )
