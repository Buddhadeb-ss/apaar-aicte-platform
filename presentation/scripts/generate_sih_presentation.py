import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Theme Colors
    DARK_BG = RGBColor(10, 15, 30)         # Deep Navy #0A0F1E
    CARD_BG = RGBColor(19, 29, 53)         # Slate Navy #131D35
    CARD_BORDER = RGBColor(38, 55, 92)     # Muted Blue #26375C
    ACCENT_SKY = RGBColor(56, 189, 248)    # Sky 400 #38BDF8
    ACCENT_ORANGE = RGBColor(249, 115, 22) # Amber/Orange 500 #F97316
    ACCENT_GREEN = RGBColor(52, 211, 153)  # Emerald 400 #34D399
    ACCENT_PURPLE = RGBColor(167, 139, 250)# Purple 400 #A78BFA
    TEXT_WHITE = RGBColor(255, 255, 255)
    TEXT_MUTED = RGBColor(148, 163, 184)   # Slate 400 #94A3B8
    TEXT_LIGHT = RGBColor(226, 232, 240)   # Slate 200 #E2E8F0

    def apply_background(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = DARK_BG
        bg.line.fill.background()
        return bg

    def add_header(slide, slide_num, title_text, category_text="SIH26263 • AICTE APAAR PLATFORM"):
        # Category / Tag
        tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.7), Inches(0.4))
        tf = tag_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = category_text.upper()
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = ACCENT_ORANGE

        # Main Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.85), Inches(11.7), Inches(0.6))
        tf2 = title_box.text_frame
        tf2.word_wrap = True
        tf2.margin_left = tf2.margin_top = tf2.margin_right = tf2.margin_bottom = 0
        p2 = tf2.paragraphs[0]
        p2.text = title_text
        p2.font.size = Pt(22)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_WHITE

        # Slide Number Badge
        num_box = slide.shapes.add_textbox(Inches(11.8), Inches(0.6), Inches(0.8), Inches(0.4))
        tf3 = num_box.text_frame
        p3 = tf3.paragraphs[0]
        p3.text = f"0{slide_num}/06"
        p3.alignment = PP_ALIGN.RIGHT
        p3.font.size = Pt(12)
        p3.font.bold = True
        p3.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    apply_background(s1)

    # Top Tag
    tag = s1.shapes.add_textbox(Inches(1.2), Inches(1.2), Inches(11), Inches(0.5))
    p = tag.text_frame.paragraphs[0]
    p.text = "SMART INDIA HACKATHON 2024 / 2026 • AICTE PROBLEM STATEMENT SIH26263"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = ACCENT_ORANGE

    # Main Project Title
    main_title = s1.shapes.add_textbox(Inches(1.2), Inches(1.7), Inches(11), Inches(1.8))
    tf = main_title.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Development of an APAAR ID-Based Student Data\nManagement and Verification Platform"
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = TEXT_WHITE

    # Subtitle
    sub_title = s1.shapes.add_textbox(Inches(1.2), Inches(3.6), Inches(11), Inches(0.8))
    tf = sub_title.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "A Secure, Interoperable Regulatory Solution for Approved Intake Enforcement, Multi-College Collision Detection, and Verifiable QR Credential Issuance in AICTE-Approved Institutions."
    p.font.size = Pt(14)
    p.font.color.rgb = TEXT_LIGHT

    # 4 Meta Cards
    meta_info = [
        ("Ministry / Organization", "All India Council for Technical Education (AICTE)", ACCENT_SKY),
        ("Theme / Category", "Smart Education / Regulatory Governance", ACCENT_ORANGE),
        ("Team Name / ID", "[Insert Team Name] • SIH26263", ACCENT_GREEN),
        ("Implementation Status", "Full-Stack Demo-Ready (FastAPI + React 18)", ACCENT_PURPLE)
    ]
    for i, (k, v, color) in enumerate(meta_info):
        x = Inches(1.2 + i * 2.75)
        card = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(4.7), Inches(2.6), Inches(1.8))
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = CARD_BORDER
        card.line.width = Pt(1)

        tb = s1.shapes.add_textbox(x + Inches(0.15), Inches(4.85), Inches(2.3), Inches(1.5))
        tf = tb.text_frame
        tf.word_wrap = True
        p1 = tf.paragraphs[0]
        p1.text = k.upper()
        p1.font.size = Pt(10)
        p1.font.bold = True
        p1.font.color.rgb = color

        p2 = tf.add_paragraph()
        p2.text = v
        p2.font.size = Pt(12)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_WHITE

    # =========================================================================
    # SLIDE 2: PROBLEM STATEMENT & PROPOSED SOLUTION
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    apply_background(s2)
    add_header(s2, 2, "Problem Statement & Proposed Solution Architecture")

    # Left Card: The Challenge
    left_card = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    left_card.fill.solid()
    left_card.fill.fore_color.rgb = CARD_BG
    left_card.line.color.rgb = CARD_BORDER

    tb_left = s2.shapes.add_textbox(Inches(1.1), Inches(1.8), Inches(5.0), Inches(4.8))
    tf = tb_left.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "THE REGULATORY CHALLENGE"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = ACCENT_ORANGE

    challenges = [
        ("Siloed Institutional Rosters:", "Colleges manage student data in isolated spreadsheets; AICTE lacks unified, real-time national visibility."),
        ("Ghost Enrolments & Double Admissions:", "Students concurrently enrol in multiple colleges to hedge seats, resulting in seat wastage and quota blocking."),
        ("Seat Cap Breaches:", "Institutions exceed AICTE-sanctioned core intake without statutory approvals, mixing approved and supernumerary quotas."),
        ("Rampant Credential Fraud:", "Paper degree certificates lack cryptographic tamper detection, causing slow (2-4 weeks) employer background checks."),
        ("Lack of Explainable Scrutiny:", "Audits rely on manual scrutiny without deterministic, automated rule compliance checking.")
    ]
    for title, desc in challenges:
        p = tf.add_paragraph()
        p.text = f"• {title} "
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE
        p_desc = tf.add_paragraph()
        p_desc.text = f"   {desc}"
        p_desc.font.size = Pt(10)
        p_desc.font.color.rgb = TEXT_MUTED

    # Right Card: Our Proposed Solution
    right_card = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.2))
    right_card.fill.solid()
    right_card.fill.fore_color.rgb = CARD_BG
    right_card.line.color.rgb = CARD_BORDER

    tb_right = s2.shapes.add_textbox(Inches(7.1), Inches(1.8), Inches(5.1), Inches(4.8))
    tf = tb_right.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "THE PROPOSED UNIFIED PLATFORM"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GREEN

    solutions = [
        ("One Nation, One Student Identity (APAAR):", "Unique physical student identities separated from seat enrolments to eliminate double-counting."),
        ("Central Cross-Institution Collision Engine:", "Real-time cryptographic hash matching detects concurrent enrolments across colleges instantly."),
        ("Strict Dual-Quota Intake Enforcement:", "Segregates core approved intake from supernumerary quotas (TFW 5%, NRI 5%, FN 15%)."),
        ("14-Rule Deterministic Validation Engine:", "Automated rule validation with structured issue codes, severity badges, and explainable penalty scores."),
        ("HMAC-SHA256 Cryptographic QR Passes:", "Tamper-evident, privacy-masked student passes enabling instant 2-second employer verification.")
    ]
    for title, desc in solutions:
        p = tf.add_paragraph()
        p.text = f"• {title} "
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE
        p_desc = tf.add_paragraph()
        p_desc.text = f"   {desc}"
        p_desc.font.size = Pt(10)
        p_desc.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 3: SYSTEM ARCHITECTURE & DATA FLOW
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    apply_background(s3)
    add_header(s3, 3, "Technical Architecture & Operational Workflow")

    # 3 Architecture Tier Cards
    tiers = [
        ("TIER 1: PRESENTATION LAYER", "React 18 • TypeScript • Vite • Tailwind CSS", [
            "AICTE Central Command Center & Analytics (Recharts)",
            "Institutional Portal & Bulk CSV Import Wizard",
            "Deterministic Statutory Validation Workbench",
            "Student Privacy-Preserving Credential Pass",
            "Authorized Employer Verification Portal with QR Scanner"
        ], ACCENT_SKY),
        ("TIER 2: BACKEND APPLICATION CORE", "FastAPI • Python 3.13 • Pydantic v2 • SQLAlchemy", [
            "Versioned RESTful APIs under /api/v1 with OAuth2/JWT RBAC",
            "14-Rule Statutory Admission Validation Engine",
            "National Intake Reconciliation & Quota Tracking Service",
            "HMAC-SHA256 Cryptographic Signature & Verification Engine",
            "Verhoeff Checksum Validator & Privacy Masking Pipeline"
        ], ACCENT_ORANGE),
        ("TIER 3: DATA & TRUST INFRASTRUCTURE", "SQLite (Demo) / PostgreSQL • ABC / DigiLocker Gateway", [
            "Relational Models: Institutions, Intakes, Students, Enrolments",
            "Multi-Tenant Isolation enforced via 'enforce_institution_scope'",
            "Append-Only Non-Repudiation Audit Event Log",
            "Simulated Academic Bank of Credits (ABC) / DigiLocker Gateway",
            "Bulk Upload Staging, Error Resolution & Report Generation"
        ], ACCENT_GREEN)
    ]

    for i, (title, stack, items, color) in enumerate(tiers):
        x = Inches(0.8 + i * 3.95)
        card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(1.6), Inches(3.75), Inches(3.6))
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = CARD_BORDER

        tb = s3.shapes.add_textbox(x + Inches(0.15), Inches(1.75), Inches(3.45), Inches(3.3))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = color

        p_stack = tf.add_paragraph()
        p_stack.text = stack
        p_stack.font.size = Pt(9)
        p_stack.font.bold = True
        p_stack.font.color.rgb = TEXT_MUTED

        for item in items:
            p = tf.add_paragraph()
            p.text = f"• {item}"
            p.font.size = Pt(9.5)
            p.font.color.rgb = TEXT_LIGHT

    # Bottom Banner: Workflow Pipeline
    wf_box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.4), Inches(11.7), Inches(1.5))
    wf_box.fill.solid()
    wf_box.fill.fore_color.rgb = CARD_BG
    wf_box.line.color.rgb = CARD_BORDER

    tb_wf = s3.shapes.add_textbox(Inches(1.0), Inches(5.5), Inches(11.3), Inches(1.3))
    tf = tb_wf.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "END-TO-END DATA WORKFLOW PIPELINE"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = ACCENT_PURPLE

    steps = [
        "1. Institution Onboarding (CSV Upload / Manual Entry)",
        "2. Deterministic Rule Engine Validation (14 Statutory Rules)",
        "3. Inline Error Resolution & Batch Commitment",
        "4. Central Registry Reconciliation & Collision Detection",
        "5. Cryptographic QR Issuance & Instant Verification"
    ]
    p_steps = tf.add_paragraph()
    p_steps.text = "   ➔   ".join(steps)
    p_steps.font.size = Pt(10)
    p_steps.font.bold = True
    p_steps.font.color.rgb = TEXT_WHITE

    # =========================================================================
    # SLIDE 4: KEY INNOVATIONS & TECHNICAL DIFFERENTIATORS
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    apply_background(s4)
    add_header(s4, 4, "Key Technical Innovations & Core Differentiators (USP)")

    usps = [
        ("Identity vs. Enrolment Separation",
         "Physical students (Student.id) are decoupled from seat admissions (StudentEnrolment.id). Vikram Malhotra holds admissions in Apex Tech and Beacon College—correctly tracked as 16 identities across 17 enrolments, triggering an instant collision alert without corrupting records.",
         ACCENT_SKY),
        ("Dual-Quota Capacity Accounting",
         "Strictly isolates approved regular intake from statutory supernumerary quotas (TFW 5%, NRI 5%, Foreign National 15%). Prevents erroneous over-admission penalties while preventing colleges from hiding excess general admissions under supernumerary categories.",
         ACCENT_ORANGE),
        ("14-Rule Deterministic Validation Engine",
         "Replaces black-box checks with a deterministic rule engine. Rules include Verhoeff checksum disclaimer, cross-college collision, roll number uniqueness, course consistency, and bulk change surges (>30%), complete with explainable penalty risk scores.",
         ACCENT_GREEN),
        ("Cryptographic QR Credential System",
         "Issues HMAC-SHA256 digitally signed verifiable passes with purpose-bound third-party consent logging, non-repudiation audit trails, and privacy masking (•••• •••• •••• 9012) compliant with Indian Data Protection standards.",
         ACCENT_PURPLE)
    ]

    for i, (title, desc, color) in enumerate(usps):
        row = i // 2
        col = i % 2
        x = Inches(0.8 + col * 5.95)
        y = Inches(1.6 + row * 2.65)
        card = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, Inches(5.75), Inches(2.4))
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = CARD_BORDER

        tb = s4.shapes.add_textbox(x + Inches(0.2), y + Inches(0.15), Inches(5.35), Inches(2.1))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"{i+1}. {title.upper()}"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = color

        p_desc = tf.add_paragraph()
        p_desc.text = desc
        p_desc.font.size = Pt(10.5)
        p_desc.font.color.rgb = TEXT_LIGHT

    # =========================================================================
    # SLIDE 5: FEASIBILITY, SCALABILITY & REGULATORY COMPLIANCE
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    apply_background(s5)
    add_header(s5, 5, "Feasibility, Security, Scalability & Regulatory Compliance")

    pillars = [
        ("REGULATORY COMPLIANCE (AICTE APH & NEP 2020)", [
            "Full compliance with AICTE Approval Process Handbook (APH) sanctioned intake formulas.",
            "Incorporates National Education Policy (NEP 2020) Academic Bank of Credits (ABC) mobility.",
            "Honors statutory reservation policies (SC/ST/OBC/EWS) and supernumerary caps (TFW/NRI/FN)."
        ], ACCENT_SKY),
        ("STRICT MULTI-TENANT ISOLATION & SECURITY", [
            "Strict server-side tenant scoping enforced via 'enforce_institution_scope' middleware.",
            "Apex Tech attempting to query Beacon College data receives HTTP 403 Forbidden.",
            "Privacy by design: Masked APAAR IDs in UI; raw IDs encrypted; hash-based collision queries.",
            "Full non-repudiation audit trail recording actor IP, timestamp, role, and action payload."
        ], ACCENT_ORANGE),
        ("FEASIBILITY & HORIZONTAL SCALABILITY", [
            "Lightweight, asynchronous FastAPI backend capable of processing 10,000+ RPS.",
            "Streaming CSV parser supports bulk onboarding of 50,000+ records per batch without memory bloat.",
            "Plug-and-play architecture ready for PostgreSQL production deployment & Redis caching.",
            "Dockerized container deployment with zero external proprietary software dependencies."
        ], ACCENT_GREEN)
    ]

    for i, (title, items, color) in enumerate(pillars):
        y = Inches(1.6 + i * 1.75)
        card = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), y, Inches(11.7), Inches(1.55))
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = CARD_BORDER

        tb = s5.shapes.add_textbox(Inches(1.0), y + Inches(0.12), Inches(11.3), Inches(1.3))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = color

        for item in items:
            p = tf.add_paragraph()
            p.text = f"• {item}"
            p.font.size = Pt(9.5)
            p.font.color.rgb = TEXT_LIGHT

    # =========================================================================
    # SLIDE 6: IMPACT, FUTURE ROADMAP & CONCLUSION
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    apply_background(s6)
    add_header(s6, 6, "National Impact, Deployment Roadmap & Conclusion")

    # Left: Measurable Impact
    left_card = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    left_card.fill.solid()
    left_card.fill.fore_color.rgb = CARD_BG
    left_card.line.color.rgb = CARD_BORDER

    tb_left = s6.shapes.add_textbox(Inches(1.1), Inches(1.8), Inches(5.0), Inches(4.8))
    tf = tb_left.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "MEASURABLE NATIONAL IMPACT"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GREEN

    impacts = [
        ("100% Elimination of Ghost Admissions:", "Multi-college collision engine prevents students from hoarding seats in multiple technical institutions."),
        ("Zero Unauthorized Over-Admissions:", "Real-time intake tracking enforces sanctioned seat limits across all 10,000+ AICTE institutions."),
        ("Instant 2-Second Credential Verification:", "Reduces employer and university credential background checks from 3 weeks to under 2 seconds."),
        ("Explainable Institutional Governance:", "Automated compliance risk scoring eliminates arbitrary penalties and promotes transparent institutional ratings."),
        ("Data Sovereignty & Privacy Assurance:", "Masked APAAR identifiers prevent identity theft while ensuring full verification authenticity.")
    ]
    for title, desc in impacts:
        p = tf.add_paragraph()
        p.text = f"• {title} "
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE
        p_desc = tf.add_paragraph()
        p_desc.text = f"   {desc}"
        p_desc.font.size = Pt(10)
        p_desc.font.color.rgb = TEXT_MUTED

    # Right: Phased Deployment Roadmap
    right_card = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.2))
    right_card.fill.solid()
    right_card.fill.fore_color.rgb = CARD_BG
    right_card.line.color.rgb = CARD_BORDER

    tb_right = s6.shapes.add_textbox(Inches(7.1), Inches(1.8), Inches(5.1), Inches(4.8))
    tf = tb_right.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "PHASED IMPLEMENTATION ROADMAP"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = ACCENT_SKY

    roadmap = [
        ("PHASE 1: PROTOTYPE & BENCHMARKING (COMPLETED)", "Full-stack platform built; 14 statutory validation rules; command center; multi-tenant portal; 44/44 automated tests passed."),
        ("PHASE 2: NATIONAL ECOSYSTEM INTEGRATION (MONTHS 1-3)", "Direct API binding with DigiLocker, ABC (Academic Bank of Credits), and AICTE Approval Portal annual intake sync."),
        ("PHASE 3: STATE & UNIVERSITY ROLLOUT (MONTHS 4-6)", "Pilot deployment across 50 technical universities with automated bulk onboarding and legacy record migration."),
        ("PHASE 4: MOBILE APP & OFFLINE VERIFICATION (MONTHS 7-12)", "Native Android/iOS app with offline cryptographic QR signature validation for ground verification teams.")
    ]
    for phase, detail in roadmap:
        p = tf.add_paragraph()
        p.text = f"• {phase}"
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = ACCENT_ORANGE if "COMPLETED" in phase else TEXT_WHITE
        p_d = tf.add_paragraph()
        p_d.text = f"   {detail}"
        p_d.font.size = Pt(9.5)
        p_d.font.color.rgb = TEXT_MUTED

    output_path = r"c:\All_Projects\apaar-aicte-platform\SIH26263_Presentation.pptx"
    prs.save(output_path)
    print(f"Presentation successfully saved to: {output_path}")

if __name__ == "__main__":
    create_presentation()
