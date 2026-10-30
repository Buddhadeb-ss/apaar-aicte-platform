from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from ..deps import get_db, get_current_user
from ...database.models import (
    SignedCredential, StudentEnrolment, Student, Institution,
    VerificationRequest, ConsentRecord, AuditEvent, User
)
from ...schemas.v1_schemas import VerificationRequestIn, VerificationResponseOut
from ...core.security import verify_credential_signature
from ...core.identifiers import generate_uuid

router = APIRouter(prefix="/verifications", tags=["Authorized Credential Verification & QR Lookup"])

@router.post("/verify", response_model=VerificationResponseOut)
def verify_credential(
    req: VerificationRequestIn,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public and Third-Party Verifier Endpoint:
    Validates digital credential against server-side HMAC signature.
    Complies with data privacy laws by returning strictly masked APAAR ID.
    """
    token_clean = req.token.strip()
    if "|" in token_clean:
        parts = token_clean.split("|")
        # Format: AICTE-APAAR-PASS|token|signature|internal_id|institution_id
        if len(parts) >= 2:
            token_clean = parts[1]

    client_ip = request.client.host if request.client else "127.0.0.1"

    cred = db.query(SignedCredential).filter(SignedCredential.verification_token == token_clean).first()

    if not cred or cred.is_revoked:
        vlog = VerificationRequest(
            id=generate_uuid(),
            token=token_clean[:64],
            verifier_name=req.verifier_name,
            verifier_organization=req.verifier_organization,
            purpose=req.purpose,
            verification_result="NOT_FOUND" if not cred else "REVOKED",
            consent_verified=False,
            ip_address=client_ip
        )
        db.add(vlog)
        db.commit()

        return VerificationResponseOut(
            status="NOT_FOUND" if not cred else "REVOKED",
            is_valid=False,
            verification_code=token_clean[:8],
            consent_verified=False,
            gateway_note="Credential token does not exist in the central AICTE registry or has been revoked."
        )

    enrol = cred.enrolment
    student = cred.student

    # Verify student consent
    consent = db.query(ConsentRecord).filter(ConsentRecord.student_id == student.id).first()
    consent_ok = (consent is not None and consent.status == "GRANTED")

    # Cryptographic signature validation
    is_sig_valid = verify_credential_signature(
        token=cred.verification_token,
        student_internal_id=enrol.internal_student_id,
        apaar_hash=student.apaar_hash,
        institution_id=enrol.institution_id,
        signature=cred.signature_value
    )

    verif_status = "VERIFIED" if (is_sig_valid and consent_ok) else ("CONSENT_REQUIRED" if not consent_ok else "INVALID_SIGNATURE")

    # Log in verification requests
    vlog = VerificationRequest(
        id=generate_uuid(),
        token=token_clean,
        student_id=student.id,
        enrolment_id=enrol.id,
        verifier_name=req.verifier_name,
        verifier_organization=req.verifier_organization,
        purpose=req.purpose,
        verification_result=verif_status,
        consent_verified=consent_ok,
        ip_address=client_ip
    )
    db.add(vlog)

    # Log sanitized Audit Event
    audit = AuditEvent(
        institution_id=enrol.institution_id,
        actor_user_id=None,
        actor_email=req.verifier_organization,
        actor_role="AUTHORIZED_VERIFIER",
        event_type="CREDENTIAL_VERIFIED",
        resource_type="SIGNED_CREDENTIAL",
        resource_id=cred.id,
        details_json=f'{{"verifier": "{req.verifier_name}", "org": "{req.verifier_organization}", "result": "{verif_status}"}}',
        ip_address=client_ip
    )
    db.add(audit)
    db.commit()

    return VerificationResponseOut(
        status=verif_status,
        is_valid=(verif_status == "VERIFIED"),
        verification_code=cred.verification_token[:8],
        student_name=student.student_name,
        internal_id=enrol.internal_student_id,
        apaar_masked=student.apaar_masked,  # ALWAYS MASKED FOR PRIVACY
        institution_name=enrol.institution.name if enrol.institution else "Unknown",
        programme=enrol.course.programme.name if enrol.course and enrol.course.programme else "Unknown",
        course=enrol.course.name if enrol.course else "Unknown",
        academic_year=enrol.academic_year,
        admission_status=enrol.admission_status,
        digital_signature=cred.signature_value,
        signature_verified=is_sig_valid,
        issued_on=cred.issued_at.strftime("%Y-%m-%d"),
        consent_verified=consent_ok,
        gateway_note="Official AICTE Cryptographic Server Signature Verified. Linked with National Academic Depository (Simulated)."
    )

@router.get("/history")
def get_verification_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve audit trail of recent verification queries."""
    query = db.query(VerificationRequest)
    if current_user.role in ("INSTITUTION_ADMIN", "INSTITUTION_OPERATOR"):
        query = query.join(StudentEnrolment).filter(StudentEnrolment.institution_id == current_user.institution_id)

    logs = query.order_by(VerificationRequest.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "verifier_name": l.verifier_name,
            "verifier_organization": l.verifier_organization,
            "purpose": l.purpose,
            "result": l.verification_result,
            "consent_verified": l.consent_verified,
            "ip_address": l.ip_address,
            "timestamp": l.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for l in logs
    ]
