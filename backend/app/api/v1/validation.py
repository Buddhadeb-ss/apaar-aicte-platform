import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from ..deps import get_db, get_current_user, enforce_institution_scope
from ...database.models import (
    BulkUploadJob, ValidationIssue, Institution, Course, Student,
    StudentEnrolment, SignedCredential, ConsentRecord, AuditEvent, User
)
from ...schemas.v1_schemas import (
    ValidationIssueOut, BatchResolveIn,
    ValidationWorkbenchIssueOut, ValidationWorkbenchSummary,
    ValidationWorkbenchResponse, IssueStatusUpdateIn,
    BulkIssueReviewIn, ValidationAuditResponse
)
from ...core.identifiers import (
    generate_uuid, normalize_identifier, validate_apaar_format,
    mask_apaar_id, hash_apaar_id
)
from ...core.security import generate_credential_signature
from ...core.validation_engine import ValidationEngine

router = APIRouter(prefix="/validation", tags=["Validation Issues & Error Resolution"])

def serialize_workbench_issue(issue: ValidationIssue) -> ValidationWorkbenchIssueOut:
    raw = {}
    if issue.raw_data_json:
        try:
            raw = json.loads(issue.raw_data_json)
        except Exception:
            raw = {"raw": issue.raw_data_json}

    inst_name = issue.institution.name if issue.institution else (
        issue.job.institution.name if issue.job and issue.job.institution else None
    )
    
    student_name = issue.student.student_name if issue.student else raw.get("student_name")
    internal_id = None
    if issue.enrolment:
        internal_id = issue.enrolment.internal_student_id
        if not student_name and issue.enrolment.student:
            student_name = issue.enrolment.student.student_name
    elif "internal_student_id" in raw or "internal_id" in raw or "internal_roll" in raw:
        internal_id = raw.get("internal_student_id") or raw.get("internal_id") or raw.get("internal_roll")
    
    apaar_masked = None
    if issue.student and issue.student.apaar_masked:
        apaar_masked = issue.student.apaar_masked
    elif issue.enrolment and issue.enrolment.student and issue.enrolment.student.apaar_masked:
        apaar_masked = issue.enrolment.student.apaar_masked
    elif "apaar_id" in raw:
        clean = str(raw.get("apaar_id") or "").replace(" ", "").replace("-", "")
        if len(clean) >= 4:
            apaar_masked = f"XXXXXXXX{clean[-4:]}"

    status_str = issue.resolution_status or "NEW"
    if status_str == "PENDING":
        status_str = "NEW"

    is_anomaly = (
        "potential anomaly" in (issue.error_message or "").lower()
        or issue.rule_id in ("RULE_04_CROSS_INST_DUPLICATE", "RULE_12_CONFLICTING_ATTRIBUTES", "RULE_14_SUSPICIOUS_BULK_CHANGE")
        or issue.error_code == "POTENTIAL_DUPLICATE_IDENTITY_MATCH"
    )

    return ValidationWorkbenchIssueOut(
        id=issue.id,
        job_id=issue.job_id,
        institution_id=issue.institution_id or (issue.job.institution_id if issue.job else None),
        institution_name=inst_name,
        student_id=issue.student_id,
        enrolment_id=issue.enrolment_id,
        row_number=issue.row_number,
        rule_id=issue.rule_id or "RULE_UNKNOWN",
        field_name=issue.field_name,
        error_code=issue.error_code,
        error_message=issue.error_message,
        suggested_remediation=issue.suggested_remediation or "Review record details and align with regulatory guidelines.",
        severity=issue.severity or "CRITICAL",
        anomaly_score=issue.anomaly_score or 0.0,
        is_potential_anomaly=is_anomaly,
        resolution_status=status_str,
        raw_data=raw,
        reviewed_by_user_id=issue.reviewed_by_user_id,
        reviewed_by_email=issue.reviewed_by_email,
        reviewed_at=issue.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if issue.reviewed_at else None,
        resolution_reason=issue.resolution_reason,
        created_at=issue.created_at.strftime("%Y-%m-%d %H:%M:%S") if issue.created_at else None,
        updated_at=issue.updated_at.strftime("%Y-%m-%d %H:%M:%S") if issue.updated_at else None,
        student_name=student_name,
        internal_student_id=internal_id,
        apaar_masked=apaar_masked
    )

# ----------------- 1. VALIDATION WORKBENCH -----------------

@router.get("/workbench", response_model=ValidationWorkbenchResponse)
def get_validation_workbench(
    institution_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    rule_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Central statutory validation workbench providing:
    - Multi-criteria filtering (severity, status, rule ID, search)
    - Full issue counts across categories
    - Explainable risk & anomaly scores
    - Tenant isolation: Institution users only access their own issues; AICTE Admin can inspect any.
    """
    if current_user.role in ("INSTITUTION_ADMIN", "INSTITUTION_OPERATOR", "INSTITUTE_ADMIN"):
        target_inst_id = current_user.institution_id
    elif current_user.role == "AICTE_ADMIN":
        target_inst_id = institution_id
    else:
        raise HTTPException(status_code=403, detail="Unauthorized to access validation workbench.")

    base_query = db.query(ValidationIssue)
    if target_inst_id:
        base_query = base_query.outerjoin(BulkUploadJob, ValidationIssue.job_id == BulkUploadJob.id).filter(
            or_(
                ValidationIssue.institution_id == target_inst_id,
                BulkUploadJob.institution_id == target_inst_id
            )
        )

    # 1. Compute summary counts across tenant's total issues
    all_tenant_issues = base_query.all()
    total_issues = len(all_tenant_issues)
    critical_c = 0
    high_c = 0
    med_c = 0
    low_c = 0
    new_c = 0
    under_review_c = 0
    resolved_c = 0
    dismissed_c = 0
    rule_breakdown: Dict[str, int] = {}
    active_anomaly_score = 0.0

    for iss in all_tenant_issues:
        sev = (iss.severity or "CRITICAL").upper()
        if sev == "CRITICAL":
            critical_c += 1
        elif sev == "HIGH":
            high_c += 1
        elif sev == "MEDIUM":
            med_c += 1
        elif sev == "LOW":
            low_c += 1

        st = (iss.resolution_status or "NEW").upper()
        if st in ("NEW", "PENDING"):
            new_c += 1
            active_anomaly_score += (iss.anomaly_score or 15.0)
        elif st == "UNDER_REVIEW":
            under_review_c += 1
            active_anomaly_score += (iss.anomaly_score or 15.0) * 0.5
        elif st == "RESOLVED":
            resolved_c += 1
        elif st == "DISMISSED":
            dismissed_c += 1

        r = iss.rule_id or "RULE_UNKNOWN"
        rule_breakdown[r] = rule_breakdown.get(r, 0) + 1

    capped_score = min(100.0, round(active_anomaly_score, 1))
    if capped_score >= 70 or (critical_c > 0 and capped_score >= 50):
        risk_lvl = "CRITICAL"
    elif capped_score >= 40:
        risk_lvl = "HIGH"
    elif capped_score >= 20:
        risk_lvl = "MEDIUM"
    else:
        risk_lvl = "LOW"

    # 2. Filter dataset for current view
    filtered_query = base_query
    if severity:
        filtered_query = filtered_query.filter(ValidationIssue.severity == severity.upper())
    if status:
        st_upper = status.upper()
        if st_upper == "NEW":
            filtered_query = filtered_query.filter(ValidationIssue.resolution_status.in_(["NEW", "PENDING"]))
        else:
            filtered_query = filtered_query.filter(ValidationIssue.resolution_status == st_upper)
    if rule_id:
        filtered_query = filtered_query.filter(ValidationIssue.rule_id == rule_id)
    if search:
        s_term = f"%{search.strip()}%"
        filtered_query = filtered_query.filter(
            or_(
                ValidationIssue.error_message.ilike(s_term),
                ValidationIssue.error_code.ilike(s_term),
                ValidationIssue.field_name.ilike(s_term),
                ValidationIssue.suggested_remediation.ilike(s_term),
                ValidationIssue.raw_data_json.ilike(s_term)
            )
        )

    total_filtered = filtered_query.count()
    total_pages = max(1, (total_filtered + limit - 1) // limit)
    offset = (page - 1) * limit

    items = filtered_query.order_by(ValidationIssue.id.desc()).offset(offset).limit(limit).all()

    summary = ValidationWorkbenchSummary(
        total_issues=total_issues,
        critical_count=critical_c,
        high_count=high_c,
        medium_count=med_c,
        low_count=low_c,
        new_count=new_c,
        under_review_count=under_review_c,
        resolved_count=resolved_c,
        dismissed_count=dismissed_c,
        anomaly_score=capped_score,
        risk_level=risk_lvl,
        is_potential_anomaly=(capped_score >= 40 or any("potential anomaly" in i.error_message.lower() for i in all_tenant_issues)),
        rule_breakdown=rule_breakdown
    )

    return ValidationWorkbenchResponse(
        items=[serialize_workbench_issue(i) for i in items],
        summary=summary,
        total=total_filtered,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

# ----------------- 2. ISSUE DETAIL & LIFECYCLE -----------------

@router.get("/issues/{id_or_job_id}")
def get_validation_issue_or_job_issues(
    id_or_job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Unified issue retriever:
    - If identifier is integer (e.g. 1, 2, 42), returns single ValidationWorkbenchIssueOut.
    - If identifier is UUID (bulk upload job ID), returns List[ValidationIssueOut] for that job.
    """
    if id_or_job_id.isdigit():
        issue_id = int(id_or_job_id)
        issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
        if not issue:
            raise HTTPException(status_code=404, detail="Validation issue not found.")
        target_inst = issue.institution_id or (issue.job.institution_id if issue.job else None)
        if target_inst:
            enforce_institution_scope(current_user, target_inst)
        return serialize_workbench_issue(issue)
    else:
        job = db.query(BulkUploadJob).filter(BulkUploadJob.id == id_or_job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Upload job not found.")
        enforce_institution_scope(current_user, job.institution_id)
        issues = db.query(ValidationIssue).filter(
            ValidationIssue.job_id == id_or_job_id,
            ValidationIssue.resolution_status.in_(["PENDING", "NEW"])
        ).order_by(ValidationIssue.row_number).all()
        results = []
        for i in issues:
            raw = {}
            if i.raw_data_json:
                try:
                    raw = json.loads(i.raw_data_json)
                except Exception:
                    raw = {}
            results.append(ValidationIssueOut(
                id=i.id,
                job_id=i.job_id,
                institution_id=i.institution_id or job.institution_id,
                student_id=i.student_id,
                enrolment_id=i.enrolment_id,
                row_number=i.row_number,
                rule_id=i.rule_id or "RULE_UNKNOWN",
                field_name=i.field_name,
                error_code=i.error_code,
                error_message=i.error_message,
                suggested_remediation=i.suggested_remediation,
                severity=i.severity or "CRITICAL",
                anomaly_score=i.anomaly_score or 0.0,
                raw_data=raw,
                resolution_status=i.resolution_status,
                reviewed_by_user_id=i.reviewed_by_user_id,
                reviewed_by_email=i.reviewed_by_email,
                reviewed_at=i.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if i.reviewed_at else None,
                resolution_reason=i.resolution_reason,
                created_at=i.created_at.strftime("%Y-%m-%d %H:%M:%S") if i.created_at else None
            ))
        return results

@router.patch("/issues/{issue_id}", response_model=ValidationWorkbenchIssueOut)
def update_validation_issue_status(
    issue_id: int,
    req: IssueStatusUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lifecycle transition for a validation issue:
    States: NEW -> UNDER_REVIEW -> RESOLVED / DISMISSED
    Mandatory reviewer attribution, timestamp, and audit trail reason.
    """
    if current_user.role not in ("AICTE_ADMIN", "INSTITUTION_ADMIN", "INSTITUTION_OPERATOR", "INSTITUTE_ADMIN"):
        raise HTTPException(status_code=403, detail="Unauthorized to manage validation issues.")

    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Validation issue not found.")

    target_inst = issue.institution_id or (issue.job.institution_id if issue.job else None)
    if target_inst:
        enforce_institution_scope(current_user, target_inst)

    valid_statuses = {"NEW", "UNDER_REVIEW", "RESOLVED", "DISMISSED"}
    target_status = req.resolution_status.upper()
    if target_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{req.resolution_status}'. Allowed: {', '.join(sorted(valid_statuses))}"
        )

    now = datetime.now(timezone.utc)
    old_status = issue.resolution_status
    issue.resolution_status = target_status
    issue.resolution_reason = req.resolution_reason
    issue.reviewed_by_user_id = current_user.id
    issue.reviewed_by_email = current_user.email
    issue.reviewed_at = now
    if target_status == "RESOLVED":
        issue.resolved_at = now

    audit = AuditEvent(
        institution_id=target_inst,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        event_type="VALIDATION_ISSUE_STATUS_UPDATED",
        resource_type="VALIDATION_ISSUE",
        resource_id=str(issue.id),
        details_json=json.dumps({
            "previous_status": old_status,
            "new_status": target_status,
            "reason": req.resolution_reason,
            "rule_id": issue.rule_id,
            "error_code": issue.error_code
        })
    )
    db.add(audit)
    db.commit()
    db.refresh(issue)

    return serialize_workbench_issue(issue)

# ----------------- 3. BULK REVIEW -----------------

@router.post("/issues/bulk-review")
def bulk_review_validation_issues(
    req: BulkIssueReviewIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Safely transition multiple validation issues in bulk:
    Enforces tenant permission boundaries and applies mandatory reason notes.
    """
    if current_user.role not in ("AICTE_ADMIN", "INSTITUTION_ADMIN", "INSTITUTION_OPERATOR", "INSTITUTE_ADMIN"):
        raise HTTPException(status_code=403, detail="Unauthorized to review validation issues in bulk.")

    target_status = req.resolution_status.upper()
    valid_statuses = {"UNDER_REVIEW", "RESOLVED", "DISMISSED"}
    if target_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid target status '{req.resolution_status}'. Allowed: {', '.join(sorted(valid_statuses))}"
        )

    now = datetime.now(timezone.utc)
    updated_count = 0

    issues = db.query(ValidationIssue).filter(ValidationIssue.id.in_(req.issue_ids)).all()
    for issue in issues:
        target_inst = issue.institution_id or (issue.job.institution_id if issue.job else None)
        if target_inst and current_user.role in ("INSTITUTION_ADMIN", "INSTITUTION_OPERATOR", "INSTITUTE_ADMIN"):
            if current_user.institution_id != target_inst:
                continue

        issue.resolution_status = target_status
        issue.resolution_reason = req.resolution_reason
        issue.reviewed_by_user_id = current_user.id
        issue.reviewed_by_email = current_user.email
        issue.reviewed_at = now
        if target_status == "RESOLVED":
            issue.resolved_at = now
        updated_count += 1

    audit = AuditEvent(
        institution_id=current_user.institution_id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        event_type="VALIDATION_ISSUES_BULK_REVIEWED",
        resource_type="VALIDATION_ISSUE_BATCH",
        resource_id=f"count:{updated_count}",
        details_json=json.dumps({
            "status": target_status,
            "reason": req.resolution_reason,
            "updated_count": updated_count
        })
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "updated_count": updated_count}

# ----------------- 4. ON-DEMAND STATUTORY AUDIT SCAN -----------------

@router.post("/run-audit", response_model=ValidationAuditResponse)
def trigger_institution_audit(
    institution_id: Optional[str] = Query(None),
    academic_year: str = Query("2024-2025"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Triggers an on-demand, deterministic statutory audit scan across all 14 rules
    for an institution's active records and persists newly discovered issues.
    """
    if current_user.role in ("INSTITUTION_ADMIN", "INSTITUTION_OPERATOR", "INSTITUTE_ADMIN"):
        target_inst_id = current_user.institution_id
    elif current_user.role == "AICTE_ADMIN":
        target_inst_id = institution_id
        if not target_inst_id:
            first_inst = db.query(Institution).first()
            target_inst_id = first_inst.id if first_inst else None
    else:
        raise HTTPException(status_code=403, detail="Unauthorized to trigger audit scans.")

    if not target_inst_id:
        raise HTTPException(status_code=400, detail="Target institution ID is required.")

    enforce_institution_scope(current_user, target_inst_id)

    engine = ValidationEngine()
    detected_issues = engine.audit_institution(db, target_inst_id, academic_year=academic_year)
    anomaly_report = engine.calculate_anomaly_report(detected_issues)

    new_persisted = 0
    now = datetime.now(timezone.utc)
    for iss in detected_issues:
        existing = db.query(ValidationIssue).filter(
            ValidationIssue.institution_id == target_inst_id,
            ValidationIssue.rule_id == iss.rule_id,
            ValidationIssue.error_code == iss.error_code,
            ValidationIssue.enrolment_id == iss.entity_id,
            ValidationIssue.resolution_status.in_(["NEW", "PENDING", "UNDER_REVIEW"])
        ).first()

        if not existing:
            new_issue = ValidationIssue(
                institution_id=target_inst_id,
                enrolment_id=iss.entity_id,
                rule_id=iss.rule_id,
                field_name=iss.field_name,
                error_code=iss.error_code,
                error_message=iss.error_message,
                suggested_remediation=iss.suggested_remediation,
                severity=iss.severity,
                anomaly_score=iss.anomaly_score,
                raw_data_json=json.dumps(iss.metadata),
                resolution_status="NEW",
                created_at=now,
                updated_at=now
            )
            db.add(new_issue)
            new_persisted += 1

    audit_event = AuditEvent(
        institution_id=target_inst_id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        event_type="SYSTEM_VALIDATION_AUDIT_EXECUTED",
        resource_type="INSTITUTION_AUDIT",
        resource_id=target_inst_id,
        details_json=json.dumps({
            "total_issues_found": len(detected_issues),
            "new_persisted": new_persisted,
            "anomaly_score": anomaly_report.total_score,
            "risk_level": anomaly_report.risk_level
        })
    )
    db.add(audit_event)
    db.commit()

    return ValidationAuditResponse(
        status="COMPLETED",
        institution_id=target_inst_id,
        academic_year=academic_year,
        total_issues_found=len(detected_issues),
        new_issues_persisted=new_persisted,
        anomaly_score=anomaly_report.total_score,
        risk_level=anomaly_report.risk_level,
        is_potential_anomaly=anomaly_report.is_potential_anomaly,
        explanation=anomaly_report.explanation
    )

# ----------------- 5. COMPATIBILITY ENDPOINTS (JOB STAGING) -----------------



@router.post("/resolve")
def resolve_validation_issues(
    req: BatchResolveIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Inline error resolution queue:
    Takes corrected student data for staged rows, validates corrections,
    commits records to the database, and marks issues as RESOLVED.
    """
    job = db.query(BulkUploadJob).filter(BulkUploadJob.id == req.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Upload job not found.")

    enforce_institution_scope(current_user, job.institution_id)

    resolved_count = 0
    now = datetime.now(timezone.utc)

    for item in req.resolved_rows:
        issue = db.query(ValidationIssue).filter(
            ValidationIssue.id == item.issue_id,
            ValidationIssue.job_id == req.job_id
        ).first()
        if not issue:
            continue

        # 1. Validate corrected APAAR
        is_valid_ap, clean_ap, ap_err = validate_apaar_format(item.apaar_id)
        if not is_valid_ap:
            raise HTTPException(status_code=422, detail=f"Row #{issue.row_number} APAAR error: {ap_err}")

        # 2. Normalize and check roll number
        norm_roll = normalize_identifier(item.internal_student_id)
        existing = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == job.institution_id,
            StudentEnrolment.academic_year == job.academic_year,
            StudentEnrolment.internal_student_id == norm_roll
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Roll number '{norm_roll}' already exists in institutional database.")

        course = db.query(Course).filter(Course.id == item.course_id).first()
        if not course:
            course = db.query(Course).first()

        ap_hash = hash_apaar_id(clean_ap)
        ap_mask = mask_apaar_id(clean_ap)

        # Check collision
        collision = db.query(StudentEnrolment).join(Student).filter(
            Student.apaar_hash == ap_hash,
            StudentEnrolment.institution_id != job.institution_id,
            StudentEnrolment.academic_year == job.academic_year,
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
                student_name=item.student_name.strip(),
                date_of_birth=item.date_of_birth.strip(),
                gender="MALE",
                category=item.category.upper(),
                apaar_id_encrypted=clean_ap,
                apaar_hash=ap_hash,
                apaar_masked=ap_mask
            )
            db.add(student_rec)
            db.flush()

        enrol_rec = StudentEnrolment(
            id=generate_uuid(),
            student_id=student_rec.id,
            internal_student_id=norm_roll,
            institution_id=job.institution_id,
            course_id=course.id,
            academic_year=job.academic_year,
            admission_year=2024,
            admission_category="REGULAR",
            is_supernumerary=(item.supernumerary_type != "NONE"),
            supernumerary_type=item.supernumerary_type.upper(),
            admission_status="ENROLLED",
            record_status=rec_status,
            discrepancy_reason=disc_reason
        )
        db.add(enrol_rec)
        db.flush()

        vtoken = generate_uuid()
        sig = generate_credential_signature(vtoken, norm_roll, ap_hash, job.institution_id)
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

        # Mark issue resolved
        issue.resolution_status = "RESOLVED"
        issue.resolved_data_json = json.dumps(item.model_dump())
        issue.resolution_reason = "Correction submitted and student enrolled via resolution queue."
        issue.reviewed_by_user_id = current_user.id
        issue.reviewed_by_email = current_user.email
        issue.reviewed_at = now
        issue.resolved_at = now
        resolved_count += 1

    db.flush()

    job.valid_records += resolved_count
    remaining = db.query(ValidationIssue).filter(
        ValidationIssue.job_id == job.id,
        ValidationIssue.resolution_status.in_(["PENDING", "NEW"])
    ).count()
    job.error_records = remaining
    job.status = "COMPLETED" if remaining == 0 else "REQUIRES_RESOLUTION"

    audit = AuditEvent(
        institution_id=job.institution_id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        event_type="VALIDATION_ISSUES_RESOLVED",
        resource_type="BULK_UPLOAD_JOB",
        resource_id=job.id,
        details_json=f'{{"resolved_count": {resolved_count}, "remaining_errors": {remaining}}}'
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "job_status": job.status,
        "resolved_count": resolved_count,
        "remaining_error_count": remaining
    }
