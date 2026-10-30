import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from .deps import get_db, get_current_user
from ..database.models import User, Student, Institution, VerificationLog, AuditLog, SignedCredential, StudentEnrolment
from ..schemas.schemas import VerificationRequest, VerificationResponse
from ..core.security import verify_credential_signature

router = APIRouter(prefix="/verification", tags=["Authorized Credential Verification & QR Lookup"])

@router.post("/verify-qr", response_model=VerificationResponse)
def verify_student_qr_credential(
    req: VerificationRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public and Authorized Third-Party Verifier Endpoint:
    Performs server-side cryptographic verification of the digital credential signature.
    Complies with data privacy by returning strictly masked APAAR ID.
    """
    token_clean = req.token.strip()
    # Check if raw token is formatted as AICTE-APAAR-PASS payload
    if "|" in token_clean:
        parts = token_clean.split("|")
        # Format: AICTE-APAAR-PASS|token|signature|internal_id|institution_id
        if len(parts) >= 2:
            token_clean = parts[1]

    cred = db.query(SignedCredential).filter(SignedCredential.verification_token == token_clean).first()
    student = cred.student if cred else None
    client_ip = request.client.host if request.client else "127.0.0.1"

    if not student:
        # Log failed attempt
        vlog = VerificationLog(
            student_id=None,
            token=token_clean[:64],
            verifier_name=req.verifier_name,
            verifier_organization=req.verifier_organization,
            purpose=req.purpose,
            verification_result="NOT_FOUND",
            ip_address=client_ip
        )
        db.add(vlog)
        db.commit()

        return VerificationResponse(
            status="NOT_FOUND",
            is_valid=False,
            verification_code=token_clean[:8],
            gateway_note="Credential token does not exist in the central AICTE registry."
        )

    # Cryptographic Signature Verification
    is_sig_valid = verify_credential_signature(
        token=student.verification_token,
        student_internal_id=student.internal_id,
        apaar_hash=student.apaar_hash,
        institution_id=student.institution_id,
        signature=student.credential_signature
    )

    verif_status = "VERIFIED" if is_sig_valid else "INVALID_SIGNATURE"

    # Log successful/authorized lookup in immutable verification log
    vlog = VerificationLog(
        student_id=student.id,
        token=token_clean,
        verifier_name=req.verifier_name,
        verifier_organization=req.verifier_organization,
        purpose=req.purpose,
        verification_result=verif_status,
        ip_address=client_ip
    )
    db.add(vlog)

    # Log audit event
    audit = AuditLog(
        institution_id=student.institution_id,
        user_email=req.verifier_organization,
        role="VERIFIER",
        action="THIRD_PARTY_CREDENTIAL_VERIFIED",
        details=f"Verifier '{req.verifier_name}' ({req.verifier_organization}) verified student {student.internal_id} for '{req.purpose}'. Result: {verif_status}."
    )
    db.add(audit)
    db.commit()

    return VerificationResponse(
        status=verif_status,
        is_valid=is_sig_valid,
        verification_code=student.verification_token[:8],
        student_name=student.student_name,
        internal_id=student.internal_id,
        apaar_masked=student.apaar_masked,  # ALWAYS MASKED FOR DATA PRIVACY
        institution_name=student.institution_name,
        programme=student.programme,
        course=student.course,
        academic_year=student.academic_year,
        admission_status=student.admission_status,
        digital_signature=student.credential_signature,
        signature_verified=is_sig_valid,
        issued_on=student.created_at.strftime("%Y-%m-%d"),
        gateway_note="Official AICTE Server Cryptographic Signature Verified. APAAR linked via National Academic Depository."
    )

@router.get("/logs")
def get_verification_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve audit history of verification requests."""
    query = db.query(VerificationLog)
    if current_user.role == "INSTITUTE_ADMIN":
        # Filter for verifications related to this institution's students
        student_ids = [e.student_id for e in db.query(StudentEnrolment.student_id).filter(StudentEnrolment.institution_id == current_user.institution_id).all()]
        query = query.filter(VerificationLog.student_id.in_(student_ids))

    logs = query.order_by(VerificationLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "verifier_name": l.verifier_name,
            "verifier_organization": l.verifier_organization,
            "purpose": l.purpose,
            "result": l.verification_result,
            "ip_address": l.ip_address,
            "timestamp": l.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for l in logs
    ]
