import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def build_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    ASSET_DIR = r"c:\All_Projects\apaar-aicte-platform\presentation_assets"

    # Color Palette: Modern Minimalist Dark Navy & Electric Sky
    DARK_BG = RGBColor(9, 13, 22)          # Deep Charcoal Navy #090D16
    CARD_BG = RGBColor(22, 32, 54)         # Slate Navy #162036
    CARD_BORDER = RGBColor(45, 63, 102)    # Muted Outline #2D3F66
    ACCENT_SKY = RGBColor(56, 189, 248)    # Sky 400 #38BDF8
    ACCENT_AMBER = RGBColor(245, 158, 11)  # Amber 500 #F59E0B
    ACCENT_EMERALD = RGBColor(52, 211, 153)# Emerald 400 #34D399
    ACCENT_ROSE = RGBColor(244, 63, 94)    # Rose 500 #F43F5E
    TEXT_WHITE = RGBColor(255, 255, 255)
    TEXT_MUTED = RGBColor(148, 163, 184)   # Slate 400 #94A3B8
    TEXT_LIGHT = RGBColor(226, 232, 240)   # Slate 200 #E2E8F0

    def set_bg(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = DARK_BG
        bg.line.fill.background()

    def add_top_bar(slide, slide_num, category_tag, headline, subtitle=None):
        # Category Tag Pill
        tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(10.0), Inches(0.35))
        tf = tag_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = category_tag.upper()
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = ACCENT_AMBER

        # Headline
        head_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(10.0), Inches(0.6))
        tf2 = head_box.text_frame
        tf2.word_wrap = True
        tf2.margin_left = tf2.margin_top = tf2.margin_right = tf2.margin_bottom = 0
        p2 = tf2.paragraphs[0]
        p2.text = headline
        p2.font.size = Pt(28)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_WHITE

        # Subtitle
        if subtitle:
            sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.35), Inches(10.0), Inches(0.4))
            tf_sub = sub_box.text_frame
            tf_sub.word_wrap = True
            tf_sub.margin_left = tf_sub.margin_top = tf_sub.margin_right = tf_sub.margin_bottom = 0
            p_sub = tf_sub.paragraphs[0]
            p_sub.text = subtitle
            p_sub.font.size = Pt(14)
            p_sub.font.color.rgb = ACCENT_SKY

        # Slide Number Badge
        num_box = slide.shapes.add_textbox(Inches(11.5), Inches(0.4), Inches(1.0), Inches(0.35))
        tf3 = num_box.text_frame
        p3 = tf3.paragraphs[0]
        p3.text = f"0{slide_num} / 06"
        p3.alignment = PP_ALIGN.RIGHT
        p3.font.size = Pt(12)
        p3.font.bold = True
        p3.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 1: TITLE & NATIONAL VISION (Clean Minimalist with Live Hero Shot)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_bg(s1)

    # Left Column: Typography & Key Metrics
    tag1 = s1.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(5.5), Inches(0.4))
    p = tag1.text_frame.paragraphs[0]
    p.text = "SMART INDIA HACKATHON • PROBLEM STATEMENT SIH26263"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = ACCENT_AMBER

    title1 = s1.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(5.5), Inches(1.5))
    tf = title1.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "AICTE APAAR Platform"
    p.font.size = Pt(38)
    p.font.bold = True
    p.font.color.rgb = TEXT_WHITE

    sub1 = s1.shapes.add_textbox(Inches(0.8), Inches(2.2), Inches(5.5), Inches(0.8))
    tf = sub1.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "One Nation, One Student ID\nCentral Intake & Credential Registry"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = ACCENT_SKY

    # 3 Stat Pill Cards
    stats = [
        ("16 Identities ➔ 17 Enrolments", "Central Multi-College Collision Detection", ACCENT_SKY),
        ("14 Statutory Validation Rules", "Deterministic Engine with Explainable Risk Scores", ACCENT_AMBER),
        ("2-Second QR Verification", "Tamper-Proof HMAC-SHA256 Verifiable Credentials", ACCENT_EMERALD)
    ]
    for i, (metric, label, color) in enumerate(stats):
        y = Inches(3.4 + i * 1.0)
        card = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), y, Inches(5.2), Inches(0.85))
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = CARD_BORDER

        tb = s1.shapes.add_textbox(Inches(1.0), y + Inches(0.08), Inches(4.8), Inches(0.7))
        tf = tb.text_frame
        tf.word_wrap = True
        p1 = tf.paragraphs[0]
        p1.text = metric
        p1.font.size = Pt(14)
        p1.font.bold = True
        p1.font.color.rgb = color

        p2 = tf.add_paragraph()
        p2.text = label
        p2.font.size = Pt(10)
        p2.font.color.rgb = TEXT_MUTED

    # Bottom Meta
    meta1 = s1.shapes.add_textbox(Inches(0.8), Inches(6.5), Inches(5.5), Inches(0.4))
    p = meta1.text_frame.paragraphs[0]
    p.text = "Ministry of Education & AICTE  |  FastAPI + React 18 Production Build"
    p.font.size = Pt(10)
    p.font.color.rgb = TEXT_MUTED

    # Right Column: Hero Screenshot Card
    hero_pic = os.path.join(ASSET_DIR, "hero_command_center.png")
    if os.path.exists(hero_pic):
        # Outer Card frame
        f = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.3), Inches(0.8), Inches(6.3), Inches(5.9))
        f.fill.solid()
        f.fill.fore_color.rgb = CARD_BG
        f.line.color.rgb = ACCENT_SKY
        f.line.width = Pt(1.5)

        # Image inside card
        s1.shapes.add_picture(hero_pic, Inches(6.4), Inches(0.9), Inches(6.1), Inches(4.2))

        # Caption text inside card
        cap = s1.shapes.add_textbox(Inches(6.4), Inches(5.2), Inches(6.0), Inches(1.3))
        tf = cap.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = "LIVE SYSTEM DEMONSTRATION"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = ACCENT_AMBER
        p2 = tf.add_paragraph()
        p2.text = "National Command Center aggregating real-time intake caps, supernumerary quotas, and APAAR duplicate collision alerts across institutions."
        p2.font.size = Pt(10.5)
        p2.font.color.rgb = TEXT_LIGHT

    # =========================================================================
    # SLIDE 2: THE CHALLENGE VS THE BREAKTHROUGH (Minimalist Side-by-Side)
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_bg(s2)
    add_top_bar(s2, 2, "Problem vs Solution", "From Institutional Silos to Central Trust", "Eliminating ghost enrolments, seat cap breaches, and credential fraud")

    # Left Card: The Challenge (Red / Orange Outline)
    left_card = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.9), Inches(5.6), Inches(4.9))
    left_card.fill.solid()
    left_card.fill.fore_color.rgb = CARD_BG
    left_card.line.color.rgb = ACCENT_ROSE
    left_card.line.width = Pt(1.5)

    tb_left = s2.shapes.add_textbox(Inches(1.1), Inches(2.1), Inches(5.0), Inches(4.5))
    tf = tb_left.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "CURRENT REGULATORY GAPS"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = ACCENT_ROSE

    gap_bullets = [
        ("Ghost Enrolments:", "Students hold concurrent seats in multiple colleges; seats remain locked and wasted."),
        ("Seat Cap Breaches:", "Colleges exceed sanctioned intake without AICTE statutory approval."),
        ("3-Week Paper Scrutiny:", "Employers and universities endure slow, manual paper verification."),
        ("Quota Camouflage:", "Excess regular admissions disguised under supernumerary quotas."),
        ("Lack of Explainability:", "Manual scrutiny without deterministic anomaly penalty scoring.")
    ]
    for title, desc in gap_bullets:
        p = tf.add_paragraph()
        p.text = f"✕  {title} "
        p.font.size = Pt(11.5)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE
        p_d = tf.add_paragraph()
        p_d.text = f"    {desc}"
        p_d.font.size = Pt(10)
        p_d.font.color.rgb = TEXT_MUTED

    # Right Card: The Breakthrough (Sky Blue / Emerald Outline)
    right_card = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.9), Inches(5.7), Inches(4.9))
    right_card.fill.solid()
    right_card.fill.fore_color.rgb = CARD_BG
    right_card.line.color.rgb = ACCENT_EMERALD
    right_card.line.width = Pt(1.5)

    tb_right = s2.shapes.add_textbox(Inches(7.1), Inches(2.1), Inches(5.1), Inches(4.5))
    tf = tb_right.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "OUR PLATFORM BREAKTHROUGH"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = ACCENT_EMERALD

    sol_bullets = [
        ("Identity Decoupling:", "Physical student identities separated from seat enrolments to stop multi-counting."),
        ("Central Collision Engine:", "Cryptographic hash matching detects concurrent multi-college admissions instantly."),
        ("2-Second QR Verification:", "HMAC-SHA256 signed passes with verifier consent tracking and non-repudiation."),
        ("Dual-Quota Accounting:", "Sanctioned intake segregated from TFW (5%), NRI (5%), and FN (15%) quotas."),
        ("14-Rule Deterministic Engine:", "Automated rule validation with transparent penalty scores and remediation.")
    ]
    for title, desc in sol_bullets:
        p = tf.add_paragraph()
        p.text = f"✓  {title} "
        p.font.size = Pt(11.5)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE
        p_d = tf.add_paragraph()
        p_d.text = f"    {desc}"
        p_d.font.size = Pt(10)
        p_d.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 3: AICTE NATIONAL COMMAND CENTER (Live Screenshot Hero)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_bg(s3)
    add_top_bar(s3, 3, "Central Regulatory Scrutiny", "AICTE National Command Center", "Live aggregated intelligence across registered technical institutions")

    # Left Column: Key Features (38% width)
    feat_box = s3.shapes.add_textbox(Inches(0.8), Inches(1.9), Inches(4.6), Inches(4.8))
    tf = feat_box.text_frame
    tf.word_wrap = True

    features_s3 = [
        ("Zero Static Mock Data", "100% computed live from relational database models: 3 colleges, 16 student identities, 17 enrolments."),
        ("Dynamic Dimension Filters", "Filter live Recharts analytics by Academic Session (2024-2025), Programme, and State (Maharashtra, Karnataka)."),
        ("Dual-Quota Capacity Gauges", "Sanctioned core intake (600 seats) monitored separately from supernumerary admissions (5 seats)."),
        ("Explainable Institutional Review", "Transparent point-based scoring flags non-compliant campuses with explicit statutory penalty reasons.")
    ]
    for i, (title, desc) in enumerate(features_s3):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"•  {title}"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = ACCENT_SKY
        p_d = tf.add_paragraph()
        p_d.text = f"   {desc}\n"
        p_d.font.size = Pt(10)
        p_d.font.color.rgb = TEXT_LIGHT

    # Right Column: Big Crisp Screenshot (60% width)
    if os.path.exists(hero_pic):
        f = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.6), Inches(1.85), Inches(7.0), Inches(5.0))
        f.fill.solid()
        f.fill.fore_color.rgb = CARD_BG
        f.line.color.rgb = CARD_BORDER

        s3.shapes.add_picture(hero_pic, Inches(5.7), Inches(1.95), Inches(6.8), Inches(4.0))

        cap = s3.shapes.add_textbox(Inches(5.7), Inches(6.05), Inches(6.8), Inches(0.7))
        p = cap.text_frame.paragraphs[0]
        p.text = "LIVE SCREENSHOT: Command Center with 8 KPI cards, dynamic Recharts charts & directory drilldowns."
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 4: IDENTITY VS ENROLMENT DECOUPLING (Visual Collision Graphic)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_bg(s4)
    add_top_bar(s4, 4, "Core Technical USP", "Identity vs Enrolment Decoupling", "Solving the multi-college ghost enrolment dilemma without data corruption")

    # Left Column: The Concept
    tb_s4 = s4.shapes.add_textbox(Inches(0.8), Inches(1.9), Inches(4.6), Inches(4.8))
    tf = tb_s4.text_frame
    tf.word_wrap = True

    points_s4 = [
        ("The Decoupled Architecture", "Physical students (Student.id) are strictly separated from seat admissions (StudentEnrolment.id). A student can hold multiple enrolments across sessions or institutions."),
        ("Live Case Study (Vikram Malhotra)", "Vikram is concurrently enrolled in Apex Tech (B.Tech CSE) and Beacon College (B.Tech IT). The system flags 16 identities vs 17 enrolments."),
        ("SHA-256 Hashed Matching", "Privacy-preserving collision detection: matching runs on irreversible cryptographic hashes rather than exposing raw identifiers."),
        ("Non-Destructive Integrity", "Neither admission record is silently overwritten; discrepancies are flagged for authorized administrative review.")
    ]
    for i, (title, desc) in enumerate(points_s4):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"•  {title}"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = ACCENT_AMBER
        p_d = tf.add_paragraph()
        p_d.text = f"   {desc}\n"
        p_d.font.size = Pt(10)
        p_d.font.color.rgb = TEXT_LIGHT

    # Right Column: Visual Collision Graphic
    col_graphic = os.path.join(ASSET_DIR, "hero_collision_graphic.png")
    if os.path.exists(col_graphic):
        f = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.6), Inches(1.85), Inches(7.0), Inches(5.0))
        f.fill.solid()
        f.fill.fore_color.rgb = CARD_BG
        f.line.color.rgb = ACCENT_ROSE
        f.line.width = Pt(1.5)

        s4.shapes.add_picture(col_graphic, Inches(5.7), Inches(1.95), Inches(6.8), Inches(4.0))

        cap = s4.shapes.add_textbox(Inches(5.7), Inches(6.05), Inches(6.8), Inches(0.7))
        p = cap.text_frame.paragraphs[0]
        p.text = "COLLISION ENGINE: Vikram Malhotra holds seats in Apex Tech & Beacon College simultaneously."
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = ACCENT_ROSE

    # =========================================================================
    # SLIDE 5: 14-RULE DETERMINISTIC VALIDATION & WORKSPACE
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_bg(s5)
    add_top_bar(s5, 5, "Statutory Governance", "14-Rule Deterministic Validation Engine", "Structured issue codes, explainable anomaly scoring, and strict multi-tenancy")

    # Left Column: Validation Capabilities
    tb_s5 = s5.shapes.add_textbox(Inches(0.8), Inches(1.9), Inches(4.6), Inches(4.8))
    tf = tb_s5.text_frame
    tf.word_wrap = True

    points_s5 = [
        ("14 Discrete Statutory Rules", "From Verhoeff checksums (Rule 2) and duplicate roll numbers (Rule 5) to core intake overflow (Rule 9) and >30% bulk surges (Rule 14)."),
        ("Explainable Risk Scoring", "Penalty point formulas: Over-intake (+35 pts), Critical issues (+15 pts), Cross-college collisions (+25 pts). Zero black-box claims."),
        ("Strict Multi-Tenant Isolation", "Server-side scoping enforces data boundaries. Apex Tech attempting to inspect Beacon College data receives HTTP 403 Forbidden."),
        ("Bulk CSV Wizard with Preview", "Column mapping, server-side dry-run validation, row-level error reports, and atomic transactional commits.")
    ]
    for i, (title, desc) in enumerate(points_s5):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"•  {title}"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = ACCENT_EMERALD
        p_d = tf.add_paragraph()
        p_d.text = f"   {desc}\n"
        p_d.font.size = Pt(10)
        p_d.font.color.rgb = TEXT_LIGHT

    # Right Column: Institutional Workspace / Workbench Screenshot
    inst_pic = os.path.join(ASSET_DIR, "hero_institution_portal.png")
    if os.path.exists(inst_pic):
        f = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.6), Inches(1.85), Inches(7.0), Inches(5.0))
        f.fill.solid()
        f.fill.fore_color.rgb = CARD_BG
        f.line.color.rgb = CARD_BORDER

        s5.shapes.add_picture(inst_pic, Inches(5.7), Inches(1.95), Inches(6.8), Inches(4.0))

        cap = s5.shapes.add_textbox(Inches(5.7), Inches(6.05), Inches(6.8), Inches(0.7))
        p = cap.text_frame.paragraphs[0]
        p.text = "LIVE SCREENSHOT: Apex Tech Workspace with 4 course capacity allocation progress gauges."
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 6: CRYPTOGRAPHIC QR VERIFICATION & NATIONAL IMPACT
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_bg(s6)
    add_top_bar(s6, 6, "Verification & National Impact", "2-Second Verifiable Credential Verification", "Tamper-proof digital trust network with privacy by design")

    # Left Column: Student Pass Screenshot
    stud_pic = os.path.join(ASSET_DIR, "hero_student_pass.png")
    if os.path.exists(stud_pic):
        f = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.85), Inches(5.8), Inches(5.0))
        f.fill.solid()
        f.fill.fore_color.rgb = CARD_BG
        f.line.color.rgb = ACCENT_EMERALD
        f.line.width = Pt(1.5)

        s6.shapes.add_picture(stud_pic, Inches(0.9), Inches(1.95), Inches(5.6), Inches(4.0))

        cap = s6.shapes.add_textbox(Inches(0.9), Inches(6.05), Inches(5.6), Inches(0.7))
        p = cap.text_frame.paragraphs[0]
        p.text = "STUDENT CREDENTIAL PASS: Masked APAAR ID (•••• •••• •••• 9012) + HMAC-SHA256 QR code."
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = ACCENT_EMERALD

    # Right Column: National Impact & Rigor
    tb_s6 = s6.shapes.add_textbox(Inches(7.0), Inches(1.9), Inches(5.5), Inches(4.8))
    tf = tb_s6.text_frame
    tf.word_wrap = True

    impact_points = [
        ("Instant 2-Second Verification", "Prospective employers scan QR code; server validates HMAC-SHA256 cryptographic signature in under 2 seconds."),
        ("Purpose-Bound Verifier Consent", "Employer name, purpose, and IP address are logged into an append-only audit trail preventing unauthorized tracking."),
        ("Zero Ghost Admissions", "Central collision engine stops students from hoarding seats across institutions during counselling."),
        ("100% Automated Test Coverage", "44 out of 44 automated backend pytest tests passing; multi-tenant HTTP 403 blocks verified.")
    ]
    for i, (title, desc) in enumerate(impact_points):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"✓  {title}"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = ACCENT_SKY
        p_d = tf.add_paragraph()
        p_d.text = f"   {desc}\n"
        p_d.font.size = Pt(10)
        p_d.font.color.rgb = TEXT_LIGHT

    out_file = r"c:\All_Projects\apaar-aicte-platform\SIH26263_Presentation.pptx"
    prs.save(out_file)
    print(f"Visually enhanced presentation successfully saved to: {out_file}")

if __name__ == "__main__":
    build_presentation()

