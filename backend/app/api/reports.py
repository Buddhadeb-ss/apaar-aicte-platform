import io
import qrcode
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from .deps import get_db, get_current_user, enforce_institution_scope
from ..database.models import User, Institution, InstitutionCourseIntake, Student, StudentEnrolment
from ..core.security import verify_credential_signature

router = APIRouter(prefix="/reports", tags=["Official AICTE Statutory Reports & PDF Generation"])

@router.get("/institution-intake-pdf/{institution_id}")
def generate_intake_compliance_pdf(
    institution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate official AICTE Institutional Intake Compliance & Reconciliation PDF Report.
    """
    enforce_institution_scope(current_user, institution_id)
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")

    intakes = db.query(InstitutionCourseIntake).filter(InstitutionCourseIntake.institution_id == institution_id).all()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'AICTETitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0a192f'),
        alignment=1
    )
    subtitle_style = ParagraphStyle(
        'AICTESubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#475569'),
        alignment=1
    )
    header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    elements = []

    # Title & Header
    elements.append(Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION", title_style))
    elements.append(Paragraph("Statutory Regulatory Platform for APAAR ID Data Management & Intake Reconciliation", subtitle_style))
    elements.append(Spacer(1, 10))

    # Certificate Banner Box
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

    # Intake Table
    elements.append(Paragraph("PROGRAMME & COURSE-WISE INTAKE COMPLIANCE SCHEDULE", header_style))

    table_data = [
        ["Course Title", "Approved\nIntake", "Regular\nEnrolled", "TFW\nEnrolled", "NRI/FN\nEnrolled", "Variance", "Compliance Status"]
    ]

    has_violation = False
    for ci in intakes:
        course_title = ci.course.name if ci.course else "Unknown Course"
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
            has_violation = True
        elif tfw_enrolled > ci.tfw_supernumerary_quota:
            status_txt = "TFW-EXCEEDED"
            has_violation = True

        table_data.append([
            course_title,
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

    # Statutory Declaration
    dec_text = (
        "<b>STATUTORY REGULATORY ATTESTATION:</b> This document certifies that student records enrolled "
        "under APAAR IDs for the 2024-2025 academic session have been audited against the AICTE Approval "
        "Process Handbook (APH). Supernumerary intakes (TFW, NRI, FN) are audited strictly outside the regular "
        "approved intake pool as prescribed by AICTE regulations."
    )
    elements.append(Paragraph(dec_text, body_style))
    elements.append(Spacer(1, 20))

    # Sign-off box
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

@router.get("/student-credential-pdf/{student_id}")
def generate_student_credential_pdf(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate official Verifiable Student Digital Credential Pass with embedded QR code.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student record not found.")

    if current_user.role == "INSTITUTE_ADMIN":
        enforce_institution_scope(current_user, student.institution_id)
    elif current_user.role == "STUDENT":
        if student.internal_id != current_user.student_internal_id:
            raise HTTPException(status_code=403, detail="Cannot access credential of another student.")

    # Generate QR Code image in memory
    qr_payload = f"AICTE-APAAR-PASS|{student.verification_token}|{student.credential_signature}|{student.internal_id}|{student.institution_id}"
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(qr_payload)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="#0a192f", back_color="#ffffff")
    qr_buf = io.BytesIO()
    img_qr.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    # Build PDF
    pdf_buf = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buf,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CardTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#0a192f'),
        alignment=1
    )
    body_bold = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#0f172a')
    )
    body_val = ParagraphStyle(
        'BodyVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )

    elements = []

    elements.append(Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION", title_style))
    elements.append(Paragraph("<font size=10 color='#0284c7'><b>NATIONAL STUDENT APAAR CREDENTIAL PASS</b></font>", ParagraphStyle('sub', alignment=1)))
    elements.append(Spacer(1, 14))

    # Main Card
    card_rows = [
        [Paragraph("<b>Student Full Name:</b>", body_bold), Paragraph(student.student_name, body_val), ""],
        [Paragraph("<b>Institution Roll No:</b>", body_bold), Paragraph(student.internal_id, body_val), ""],
        [Paragraph("<b>Institution Name:</b>", body_bold), Paragraph(student.institution_name, body_val), ""],
        [Paragraph("<b>Programme / Course:</b>", body_bold), Paragraph(f"{student.course} ({student.programme})", body_val), ""],
        [Paragraph("<b>Academic Session:</b>", body_bold), Paragraph(f"{student.academic_year} (Year {student.admission_year})", body_val), ""],
        [Paragraph("<b>Masked APAAR ID:</b>", body_bold), Paragraph(f"<font color='#047857'><b>{student.apaar_masked}</b></font> (Verified via ABC Gateway)", body_val), ""],
        [Paragraph("<b>Category / Quota:</b>", body_bold), Paragraph(f"{student.category} | Supernumerary: {student.supernumerary_type}", body_val), ""],
        [Paragraph("<b>Admission Status:</b>", body_bold), Paragraph(f"<b>{student.admission_status}</b>", body_val), ""],
        [Paragraph("<b>Tamper-Evident Sig:</b>", body_bold), Paragraph(f"<font size=7 color='#64748b'>{student.credential_signature}</font>", body_val), ""]
    ]

    t_card = Table(card_rows, colWidths=[130, 240, 150])
    # Place QR code in the third column spanning all rows
    qr_rl_img = RLImage(qr_buf, width=130, height=130)
    t_card.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#0284c7')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('SPAN', (2,0), (2,8)),
        ('ALIGN', (2,0), (2,8), 'CENTER'),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    # Insert QR into row 0, col 2
    card_rows[0][2] = qr_rl_img
    elements.append(t_card)
    elements.append(Spacer(1, 14))

    instructions = (
        "<b>VERIFICATION INSTRUCTIONS:</b> Employers, universities, and regulatory authorities can instantly "
        "verify this credential by scanning the QR code above or visiting the AICTE APAAR Verification Portal. "
        "All queries verify the server-side HMAC-SHA256 signature without exposing the full confidential 12-digit APAAR ID."
    )
    elements.append(Paragraph(instructions, ParagraphStyle('inst', parent=styles['Normal'], fontSize=8, leading=11, textColor=colors.HexColor('#64748b'))))

    doc.build(elements)
    pdf_buf.seek(0)
    return Response(
        content=pdf_buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=APAAR_Credential_{student.internal_id}.pdf"}
    )
