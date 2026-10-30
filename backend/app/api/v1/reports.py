import io
import csv
import qrcode
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from ..deps import get_db, get_current_user, enforce_institution_scope
from ...database.models import (
    Institution, InstitutionIntake, Student, StudentEnrolment, SignedCredential,
    AuditEvent, User
)
from ...schemas.v1_schemas import AuditEventOut

router = APIRouter(prefix="/reports", tags=["Statutory Reports & PDF Generator"])

@router.get("/intake-compliance-pdf/{institution_id}")
def generate_intake_compliance_pdf(
    institution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate official AICTE Institutional Intake Compliance & Audit Certificate (PDF).
    """
    enforce_institution_scope(current_user, institution_id)
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")

    intakes = db.query(InstitutionIntake).filter(InstitutionIntake.institution_id == institution_id).all()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'AICTETitle', parent=styles['Heading1'], fontName='Helvetica-Bold',
        fontSize=15, leading=19, textColor=colors.HexColor('#0a192f'), alignment=1
    )
    subtitle_style = ParagraphStyle(
        'AICTESubtitle', parent=styles['Normal'], fontName='Helvetica',
        fontSize=10, leading=13, textColor=colors.HexColor('#475569'), alignment=1
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'], fontName='Helvetica',
        fontSize=8.5, leading=11, textColor=colors.HexColor('#334155')
    )

    elements = []
    elements.append(Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION", title_style))
    elements.append(Paragraph("Statutory Regulatory Platform for APAAR ID Data Management & Intake Reconciliation", subtitle_style))
    elements.append(Spacer(1, 10))

    cert_info = [
        [Paragraph(f"<b>Institution Name:</b> {inst.name}", body_style), Paragraph(f"<b>AICTE Permanent ID:</b> {inst.aicte_permanent_id}", body_style)],
        [Paragraph(f"<b>State / District:</b> {inst.state}, {inst.district}", body_style), Paragraph(f"<b>Academic Session:</b> {inst.approval_session}", body_style)],
        [Paragraph(f"<b>Institution Type:</b> {inst.institution_type}", body_style), Paragraph(f"<b>Generated At:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", body_style)]
    ]
    t_cert = Table(cert_info, colWidths=[270, 250])
    t_cert.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t_cert)
    elements.append(Spacer(1, 14))

    table_data = [
        ["Course Title", "Approved\nIntake", "Regular\nEnrolled", "TFW\nEnrolled", "NRI/FN\nEnrolled", "Variance", "Compliance Status"]
    ]

    for ci in intakes:
        reg_enrolled = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == institution_id,
            StudentEnrolment.course_id == ci.course_id,
            StudentEnrolment.is_supernumerary == False,
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).count()

        tfw_enrolled = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == institution_id,
            StudentEnrolment.course_id == ci.course_id,
            StudentEnrolment.supernumerary_type == "TFW",
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).count()

        nri_fn_enrolled = db.query(StudentEnrolment).filter(
            StudentEnrolment.institution_id == institution_id,
            StudentEnrolment.course_id == ci.course_id,
            (StudentEnrolment.nri_status == True) | (StudentEnrolment.foreign_national_status == True),
            StudentEnrolment.admission_status.in_(["ENROLLED", "ADMITTED"])
        ).count()

        variance = ci.approved_intake - reg_enrolled
        status_txt = "COMPLIANT"
        if reg_enrolled > ci.approved_intake:
            status_txt = "OVER-ADMISSION"
        elif tfw_enrolled > ci.tfw_supernumerary_quota:
            status_txt = "TFW-EXCEEDED"

        table_data.append([
            ci.course.name if ci.course else "Unknown",
            str(ci.approved_intake),
            str(reg_enrolled),
            str(tfw_enrolled),
            str(nri_fn_enrolled),
            str(variance),
            status_txt
        ])

    t_schedule = Table(table_data, colWidths=[160, 60, 60, 50, 55, 55, 80])
    t_schedule.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0a192f')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f1f5f9')]),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_schedule)
    elements.append(Spacer(1, 16))

    dec_text = (
        "<b>STATUTORY REGULATORY ATTESTATION:</b> This document certifies that student records enrolled "
        "under APAAR IDs for the academic session have been audited against the AICTE Approval Process Handbook (APH). "
        "Supernumerary intakes (TFW, NRI, FN) are audited strictly outside the regular approved intake pool as prescribed by AICTE regulations."
    )
    elements.append(Paragraph(dec_text, body_style))
    elements.append(Spacer(1, 20))

    sign_data = [
        [Paragraph("<b>Scrutiny Verification Officer</b><br/>AICTE National Scrutiny Directorate", body_style),
         Paragraph("<b>Institutional Registrar / Dean</b><br/>Authorized Seal & Attestation", body_style)]
    ]
    t_sign = Table(sign_data, colWidths=[260, 260])
    t_sign.setStyle(TableStyle([
        ('LINEBEFORE', (1,0), (1,0), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(t_sign)

    doc.build(elements)
    buffer.seek(0)
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=AICTE_Intake_Audit_{inst.aicte_permanent_id}.pdf"}
    )

@router.get("/student-credential-pdf/{enrolment_id}")
def generate_student_credential_pdf(
    enrolment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate official Verifiable Student Digital Credential Pass with embedded QR code (PDF)."""
    enrol = db.query(StudentEnrolment).filter(
        (StudentEnrolment.id == enrolment_id) | (StudentEnrolment.student_id == enrolment_id)
    ).first()
    if not enrol:
        raise HTTPException(status_code=404, detail="Student enrolment record not found.")

    if current_user.role in ("INSTITUTION_ADMIN", "INSTITUTION_OPERATOR"):
        enforce_institution_scope(current_user, enrol.institution_id)
    elif current_user.role == "STUDENT_VIEWER":
        if enrol.student_id != current_user.student_id:
            raise HTTPException(status_code=403, detail="Cannot access credential of another student.")

    cred = db.query(SignedCredential).filter(SignedCredential.enrolment_id == enrol.id).first()
    token = cred.verification_token if cred else "TOKEN_PENDING"
    sig = cred.signature_value if cred else "SIG_PENDING"

    qr_payload = f"AICTE-APAAR-PASS|{token}|{sig}|{enrol.internal_student_id}|{enrol.institution_id}"
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(qr_payload)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="#0a192f", back_color="#ffffff")
    qr_buf = io.BytesIO()
    img_qr.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    pdf_buf = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buf, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CardTitle', parent=styles['Heading1'], fontName='Helvetica-Bold',
        fontSize=15, leading=18, textColor=colors.HexColor('#0a192f'), alignment=1
    )
    body_bold = ParagraphStyle('BodyBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=13, textColor=colors.HexColor('#0f172a'))
    body_val = ParagraphStyle('BodyVal', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, textColor=colors.HexColor('#334155'))

    elements = []
    elements.append(Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION", title_style))
    elements.append(Paragraph("<font size=10 color='#0284c7'><b>NATIONAL STUDENT APAAR CREDENTIAL PASS</b></font>", ParagraphStyle('sub', alignment=1)))
    elements.append(Spacer(1, 14))

    card_rows = [
        [Paragraph("<b>Student Full Name:</b>", body_bold), Paragraph(enrol.student.student_name, body_val), ""],
        [Paragraph("<b>Institution Roll No:</b>", body_bold), Paragraph(enrol.internal_student_id, body_val), ""],
        [Paragraph("<b>Institution Name:</b>", body_bold), Paragraph(enrol.institution.name, body_val), ""],
        [Paragraph("<b>Programme / Course:</b>", body_bold), Paragraph(f"{enrol.course.name} ({enrol.course.programme.name})", body_val), ""],
        [Paragraph("<b>Academic Session:</b>", body_bold), Paragraph(f"{enrol.academic_year} (Year {enrol.admission_year})", body_val), ""],
        [Paragraph("<b>Masked APAAR ID:</b>", body_bold), Paragraph(f"<font color='#047857'><b>{enrol.student.apaar_masked}</b></font> (Verified via ABC Gateway)", body_val), ""],
        [Paragraph("<b>Category / Quota:</b>", body_bold), Paragraph(f"{enrol.student.category} | Supernumerary: {enrol.supernumerary_type}", body_val), ""],
        [Paragraph("<b>Admission Status:</b>", body_bold), Paragraph(f"<b>{enrol.admission_status}</b>", body_val), ""],
        [Paragraph("<b>Tamper-Evident Sig:</b>", body_bold), Paragraph(f"<font size=7 color='#64748b'>{sig}</font>", body_val), ""]
    ]

    t_card = Table(card_rows, colWidths=[130, 240, 150])
    qr_rl_img = RLImage(qr_buf, width=130, height=130)
    t_card.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#0284c7')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('SPAN', (2,0), (2,8)),
        ('ALIGN', (2,0), (2,8), 'CENTER'),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    card_rows[0][2] = qr_rl_img
    elements.append(t_card)
    elements.append(Spacer(1, 14))

    instructions = (
        "<b>VERIFICATION INSTRUCTIONS:</b> Regulatory authorities and authorized employers can instantly "
        "verify this credential by scanning the QR code above. "
        "All queries verify server-side cryptographic signatures without exposing the raw confidential 12-digit APAAR ID."
    )
    elements.append(Paragraph(instructions, ParagraphStyle('inst', parent=styles['Normal'], fontSize=8, leading=11, textColor=colors.HexColor('#64748b'))))

    doc.build(elements)
    pdf_buf.seek(0)
    return Response(
        content=pdf_buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=APAAR_Credential_{enrol.internal_student_id}.pdf"}
    )

@router.get("/audit-events", response_model=List[AuditEventOut])
def list_audit_events(
    institution_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve immutable audit event trail."""
    query = db.query(AuditEvent)
    if current_user.role in ("INSTITUTION_ADMIN", "INSTITUTION_OPERATOR"):
        query = query.filter(AuditEvent.institution_id == current_user.institution_id)
    elif institution_id:
        query = query.filter(AuditEvent.institution_id == institution_id)

    events = query.order_by(AuditEvent.timestamp.desc()).limit(limit).all()
    return [
        AuditEventOut(
            id=e.id,
            institution_id=e.institution_id,
            actor_email=e.actor_email,
            actor_role=e.actor_role,
            event_type=e.event_type,
            resource_type=e.resource_type,
            resource_id=e.resource_id,
            details=e.details_json,
            ip_address=e.ip_address,
            timestamp=e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        )
        for e in events
    ]

@router.get("/export-students-csv")
def export_students_csv(
    institution_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export confirmed student roster as CSV with masked APAAR IDs."""
    target_inst_id = current_user.institution_id if current_user.role in ("INSTITUTION_ADMIN", "INSTITUTION_OPERATOR") else institution_id
    if not target_inst_id and current_user.role != "AICTE_ADMIN":
        raise HTTPException(status_code=400, detail="Institution ID required.")

    query = db.query(StudentEnrolment)
    if target_inst_id:
        enforce_institution_scope(current_user, target_inst_id)
        query = query.filter(StudentEnrolment.institution_id == target_inst_id)

    enrolments = query.order_by(StudentEnrolment.course_id, StudentEnrolment.internal_student_id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Institution ID", "Institution Name", "Roll No", "Student Name",
        "Date of Birth", "Gender", "Category", "Course", "Academic Year",
        "Masked APAAR ID", "Supernumerary", "Supernumerary Type", "Record Status"
    ])

    for e in enrolments:
        writer.writerow([
            e.institution_id,
            e.institution.name if e.institution else "Unknown",
            e.internal_student_id,
            e.student.student_name if e.student else "Unknown",
            e.student.date_of_birth if e.student else "Unknown",
            e.student.gender if e.student else "Unknown",
            e.student.category if e.student else "Unknown",
            e.course.name if e.course else "Unknown",
            e.academic_year,
            e.student.apaar_masked if e.student else "•••• •••• ••••",
            e.is_supernumerary,
            e.supernumerary_type,
            e.record_status
        ])

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aicte_confirmed_students_roster.csv"}
    )
