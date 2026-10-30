import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def build_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    ASSET_DIR = r"c:\All_Projects\apaar-aicte-platform\presentation_assets"

    # Color Palette matching the exact reference presentation:
    COLOR_WHITE = RGBColor(255, 255, 255)
    COLOR_BLACK = RGBColor(15, 23, 42)          # Dark Charcoal #0F172A
    COLOR_BLUE_TITLE = RGBColor(30, 58, 138)     # Royal Blue #1E3A8A
    COLOR_MUTED_TEXT = RGBColor(71, 85, 105)     # Slate 600 #475569
    COLOR_LIGHT_BG = RGBColor(248, 250, 252)     # Off-white / light slate #F8FAFC
    COLOR_BORDER = RGBColor(203, 213, 225)       # Light border #CBD5E1
    COLOR_RED_PROBLEM = RGBColor(220, 38, 38)    # Red #DC2626
    COLOR_GREEN_SOLUTION = RGBColor(5, 150, 105) # Green #059669
    COLOR_AMBER = RGBColor(217, 119, 6)          # Amber #D97706
    COLOR_SCOPE_BG = RGBColor(254, 249, 195)     # Light Yellow #FEF9C3
    COLOR_SCOPE_BORDER = RGBColor(234, 179, 8)   # Yellow Border #EAB308
    COLOR_DARK_BOX = RGBColor(15, 23, 42)        # Navy Box #0F172A

    def set_white_bg(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = COLOR_WHITE
        bg.line.fill.background()

    def add_common_header(slide, slide_num, title_text, team_name="Sentinels"):
        # Top Left Team Pill
        pill = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.6), Inches(0.35), Inches(1.8), Inches(0.85))
        pill.fill.solid()
        pill.fill.fore_color.rgb = COLOR_WHITE
        pill.line.color.rgb = COLOR_BLACK
        pill.line.width = Pt(1.5)
        p_tf = pill.text_frame
        p_tf.word_wrap = True
        p_pill = p_tf.paragraphs[0]
        p_pill.text = team_name
        p_pill.alignment = PP_ALIGN.CENTER
        p_pill.font.name = "Georgia"
        p_pill.font.size = Pt(15)
        p_pill.font.bold = True
        p_pill.font.color.rgb = COLOR_BLACK

        # Top Center Title
        title_box = slide.shapes.add_textbox(Inches(2.6), Inches(0.4), Inches(8.2), Inches(0.8))
        tf = title_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_text.upper()
        p.alignment = PP_ALIGN.CENTER
        p.font.name = "Georgia"
        p.font.size = Pt(30)
        p.font.bold = True
        p.font.color.rgb = COLOR_BLACK

        # Top Right SIH Logo Badge
        sih_badge = os.path.join(ASSET_DIR, "sih_logo_badge.png")
        if os.path.exists(sih_badge):
            slide.shapes.add_picture(sih_badge, Inches(11.1), Inches(0.25), Inches(1.8), Inches(0.6))

        # Bottom Right Slide Number
        num_box = slide.shapes.add_textbox(Inches(12.5), Inches(7.0), Inches(0.5), Inches(0.35))
        tf_num = num_box.text_frame
        p_num = tf_num.paragraphs[0]
        p_num.text = str(slide_num)
        p_num.alignment = PP_ALIGN.RIGHT
        p_num.font.name = "Georgia"
        p_num.font.size = Pt(12)
        p_num.font.bold = True
        p_num.font.color.rgb = COLOR_BLACK

    # =========================================================================
    # SLIDE 1: COVER SLIDE (Exact Reference Layout)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_white_bg(s1)

    # Top Center Title: SMART INDIA HACKATHON 2026
    sih_head = s1.shapes.add_textbox(Inches(1.0), Inches(0.4), Inches(9.8), Inches(0.7))
    tf = sih_head.text_frame
    p = tf.paragraphs[0]
    p.text = "SMART INDIA HACKATHON 2026"
    p.alignment = PP_ALIGN.CENTER
    p.font.name = "Georgia"
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLUE_TITLE

    # Top Right SIH Badge
    sih_badge = os.path.join(ASSET_DIR, "sih_logo_badge.png")
    if os.path.exists(sih_badge):
        s1.shapes.add_picture(sih_badge, Inches(11.0), Inches(0.3), Inches(1.9), Inches(0.65))

    # Top Right Links Box (Github & Demo Video)
    links_box = s1.shapes.add_textbox(Inches(10.8), Inches(1.05), Inches(2.2), Inches(0.7))
    tf_l = links_box.text_frame
    p1 = tf_l.paragraphs[0]
    p1.text = "🔗  Github Source Code"
    p1.font.size = Pt(11)
    p1.font.bold = True
    p1.font.underline = True
    p1.font.color.rgb = COLOR_BLUE_TITLE
    p2 = tf_l.add_paragraph()
    p2.text = "▶  Demo Video"
    p2.font.size = Pt(11)
    p2.font.bold = True
    p2.font.underline = True
    p2.font.color.rgb = COLOR_RED_PROBLEM

    # Project Subtitle: AEGIS style
    proj_title = s1.shapes.add_textbox(Inches(1.0), Inches(1.3), Inches(9.8), Inches(0.6))
    tf_p = proj_title.text_frame
    p = tf_p.paragraphs[0]
    p.text = "APAAR AICTE: Central Student Data Management & Verification Platform"
    p.alignment = PP_ALIGN.CENTER
    p.font.name = "Georgia"
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLACK

    # Left Column: Problem Statement & Team Details
    details_box = s1.shapes.add_textbox(Inches(0.8), Inches(2.3), Inches(6.8), Inches(4.5))
    tf_d = details_box.text_frame
    tf_d.word_wrap = True

    items_s1 = [
        ("• Problem Statement ID – ", "SIH26263"),
        ("• Problem Statement Title – ", "Development of an APAAR ID-Based Student Data Management and Verification Platform for AICTE-Approved Institutions"),
        ("• Theme – ", "Ministry of Education"),
        ("• PS Category – ", "Software"),
        ("• Team Name – ", "Sentinels")
    ]
    for i, (label, val) in enumerate(items_s1):
        p = tf_d.paragraphs[0] if i == 0 else tf_d.add_paragraph()
        p.text = label
        p.font.name = "Arial"
        p.font.size = Pt(15)
        p.font.bold = True
        p.font.color.rgb = COLOR_BLACK

        run = p.add_run()
        run.text = val
        run.font.name = "Arial"
        run.font.size = Pt(15)
        run.font.bold = (label != "• Problem Statement Title – ")
        run.font.color.rgb = COLOR_BLACK
        # Add line gap
        p.space_after = Pt(14)

    # Right Column: Big Graphic Emblem / Screenshot Hero
    hero_right = os.path.join(ASSET_DIR, "hero_command_center.png")
    if os.path.exists(hero_right):
        # Framed Card
        card = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.8), Inches(2.2), Inches(4.9), Inches(4.6))
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_LIGHT_BG
        card.line.color.rgb = COLOR_BORDER
        card.line.width = Pt(1.5)

        s1.shapes.add_picture(hero_right, Inches(7.9), Inches(2.3), Inches(4.7), Inches(3.2))

        cap = s1.shapes.add_textbox(Inches(7.9), Inches(5.6), Inches(4.7), Inches(1.1))
        tf_c = cap.text_frame
        tf_c.word_wrap = True
        p = tf_c.paragraphs[0]
        p.text = "Central AICTE Command Center"
        p.font.name = "Georgia"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = COLOR_BLUE_TITLE
        p2 = tf_c.add_paragraph()
        p2.text = "100% live database aggregations • 16 student identities • 17 seat enrolments • Real-time collision alerts."
        p2.font.size = Pt(10.5)
        p2.font.color.rgb = COLOR_MUTED_TEXT

    # =========================================================================
    # SLIDE 2: PROPOSED SOLUTION (Exact Reference Layout)
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_white_bg(s2)
    add_common_header(s2, 2, "PROPOSED SOLUTION")

    # Top Narrative Summary Paragraph (Exact format as reference)
    narr_box = s2.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(7.8), Inches(1.3))
    tf_n = narr_box.text_frame
    tf_n.word_wrap = True
    p = tf_n.paragraphs[0]
    p.text = "APAAR-AICTE is an explainable central student data management and verification platform for AICTE-approved institutions. It decouples physical student identities from seat enrolments, gives colleges real-time pre-submission intake validation, and gives regulators a single, explainable verdict backed by 14 deterministic statutory checks and an immutable audit trail — not a black-box AI model."
    p.font.name = "Georgia"
    p.font.size = Pt(13.5)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLACK

    # Top Right Illustration Card
    col_img = os.path.join(ASSET_DIR, "hero_collision_graphic.png")
    if os.path.exists(col_img):
        card = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.8), Inches(1.35), Inches(3.9), Inches(1.8))
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_LIGHT_BG
        card.line.color.rgb = COLOR_BORDER
        s2.shapes.add_picture(col_img, Inches(8.85), Inches(1.4), Inches(3.8), Inches(1.7))

    # Bottom Two Columns
    # Left Column: The Problem (Red)
    tb_prob = s2.shapes.add_textbox(Inches(0.8), Inches(2.9), Inches(5.8), Inches(4.2))
    tf_pr = tb_prob.text_frame
    tf_pr.word_wrap = True

    p = tf_pr.paragraphs[0]
    p.text = "⚠️   The Problem"
    p.font.name = "Georgia"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_RED_PROBLEM

    prob_items = [
        "Siloed Institutional Rosters: Colleges manage student data in isolated spreadsheets; AICTE lacks unified, real-time national visibility into intake cap breaches.",
        "Ghost Enrolments & Seat Hoarding: Students concurrently hold seats in multiple technical institutions during counselling, wasting precious approved capacity.",
        "Paper Fraud & Black-Box AI Risks: Degree verification takes 3+ weeks, while generic LLMs hallucinate authenticity, can't explain findings, and leak records."
    ]
    for item in prob_items:
        p = tf_pr.add_paragraph()
        p.text = f"•  {item}"
        p.font.name = "Arial"
        p.font.size = Pt(10.5)
        p.font.color.rgb = COLOR_MUTED_TEXT
        p.space_after = Pt(8)

    # Right Column: The Solution (Green)
    tb_sol = s2.shapes.add_textbox(Inches(6.8), Inches(2.9), Inches(5.8), Inches(4.2))
    tf_sol = tb_sol.text_frame
    tf_sol.word_wrap = True

    p = tf_sol.paragraphs[0]
    p.text = "🛡️   The APAAR Solution"
    p.font.name = "Georgia"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN_SOLUTION

    sol_sections = [
        ("College Portal", "Real-time completeness tracking (0% → 100%), course capacity gauges, and plain-language pre-submission alerts before formal filing."),
        ("AICTE Central Command Center", "14 deterministic checks collapsed into one verdict — COMPLIANT or ISSUE FOUND — with transparent point-based penalty scoring."),
        ("Audit & Verification Trail", "Every upload, cross-institution collision, and third-party verification is permanently logged in an append-only ledger — fully traceable, fully explainable.")
    ]
    for title, desc in sol_sections:
        p_title = tf_sol.add_paragraph()
        p_title.text = title
        p_title.font.name = "Arial"
        p_title.font.size = Pt(12)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_BLACK

        p_desc = tf_sol.add_paragraph()
        p_desc.text = desc
        p_desc.font.name = "Arial"
        p_desc.font.size = Pt(10.5)
        p_desc.font.color.rgb = COLOR_MUTED_TEXT
        p_desc.space_after = Pt(6)

    # =========================================================================
    # SLIDE 3: TECHNICAL APPROACH (Exact Reference Layout)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_white_bg(s3)
    add_common_header(s3, 3, "TECHNICAL APPROACH")

    # Workflow Process Flow Banner across top
    wf_box = s3.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(11.8), Inches(0.4))
    tf_wf = wf_box.text_frame
    p_wf = tf_wf.paragraphs[0]
    p_wf.text = "College Upload  ➔  Staging & Pre-Validation  ➔  Deterministic Validation (14 checks)  ➔  Dual-Quota Reconciliation  ➔  Collision Scrutiny  ➔  Recorded Decision & Audit"
    p_wf.font.name = "Arial"
    p_wf.font.size = Pt(10)
    p_wf.font.bold = True
    p_wf.font.color.rgb = COLOR_BLUE_TITLE

    # 6 Process Cards in Horizontal Row
    process_steps = [
        ("1. Ingestion", "CSV template, schema validation, 50MB size gate, path-traversal & header guard."),
        ("2. Format Check", "Verhoeff checksum, APAAR 12-digit format, legal student name normalization."),
        ("3. Quota & Intake", "Dual-quota accounting: approved core intake vs TFW/NRI/FN supernumerary."),
        ("4. Collision Engine", "SHA-256 duplicate detection; cross-institution student ID & roll consistency."),
        ("5. Officer Review", "Single verdict card (COMPLIANT / ISSUE FOUND); 14-rule evidence on demand."),
        ("6. Decision & QR", "HMAC-SHA256 signed QR pass; immutable statutory decision audit event.")
    ]

    for i, (stitle, sdesc) in enumerate(process_steps):
        x = Inches(0.8 + i * 1.96)
        card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(1.75), Inches(1.85), Inches(2.2))
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_LIGHT_BG
        card.line.color.rgb = COLOR_BORDER
        card.line.width = Pt(1)

        tb = s3.shapes.add_textbox(x + Inches(0.08), Inches(1.85), Inches(1.7), Inches(2.0))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = stitle
        p1.font.name = "Georgia"
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = COLOR_BLACK

        p2 = tf.add_paragraph()
        p2.text = sdesc
        p2.font.name = "Arial"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = COLOR_MUTED_TEXT

    # Bottom Left: TECH STACK with Grid
    ts_title = s3.shapes.add_textbox(Inches(0.8), Inches(4.2), Inches(4.8), Inches(0.35))
    p = ts_title.text_frame.paragraphs[0]
    p.text = "TECH STACK"
    p.font.name = "Georgia"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLACK

    tech_img = os.path.join(ASSET_DIR, "tech_stack_grid.png")
    if os.path.exists(tech_img):
        s3.shapes.add_picture(tech_img, Inches(0.8), Inches(4.6), Inches(4.8), Inches(2.3))

    # Bottom Right: Honest Scope Box (Exact reference format with yellow icon & fill)
    scope_card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.9), Inches(4.3), Inches(6.6), Inches(2.6))
    scope_card.fill.solid()
    scope_card.fill.fore_color.rgb = COLOR_SCOPE_BG
    scope_card.line.color.rgb = COLOR_SCOPE_BORDER
    scope_card.line.width = Pt(1.5)

    tb_scope = s3.shapes.add_textbox(Inches(6.1), Inches(4.45), Inches(6.2), Inches(2.3))
    tf_sc = tb_scope.text_frame
    tf_sc.word_wrap = True

    p_sc = tf_sc.paragraphs[0]
    p_sc.text = "⚠️   Honest Scope"
    p_sc.font.name = "Georgia"
    p_sc.font.size = Pt(15)
    p_sc.font.bold = True
    p_sc.font.color.rgb = COLOR_AMBER

    scope_points = [
        "The current engine uses deterministic, explainable validation rules rather than ML classifiers, neural networks, or LLMs. AI/ML-based hallucination risks are eliminated by design.",
        "Simulated DigiLocker / ABC National Academic Depository Gateway v2.4 implemented for evaluation; production sandbox binding planned.",
        "Offline QR signature verification on mobile is planned, not implemented in the current prototype."
    ]
    for sp in scope_points:
        p = tf_sc.add_paragraph()
        p.text = sp
        p.font.name = "Arial"
        p.font.size = Pt(10)
        p.font.color.rgb = COLOR_BLACK
        p.space_after = Pt(5)

    # =========================================================================
    # SLIDE 4: WORKING MODEL (Exact Reference 6-Screenshot Journey)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_white_bg(s4)
    add_common_header(s4, 4, "WORKING MODEL")

    # 6 Real UI Screenshots arranged in a 2x3 grid with connecting labels & arrows
    wm_screens = [
        ("wm_01_login.png", "1. Portal Login & Personas", Inches(0.8), Inches(1.4)),
        ("wm_02_college_portal.png", "2. College Intake Dashboard", Inches(4.8), Inches(1.4)),
        ("wm_03_command_center.png", "3. AICTE National Scrutiny", Inches(8.8), Inches(1.4)),
        ("wm_04_collision.png", "4. Collision Discrepancy", Inches(0.8), Inches(4.3)),
        ("wm_05_workbench.png", "5. 14-Rule Workbench", Inches(4.8), Inches(4.3)),
        ("wm_06_qr_verify.png", "6. Student QR Pass & Verify", Inches(8.8), Inches(4.3))
    ]

    for fname, label, x, y in wm_screens:
        fpath = os.path.join(ASSET_DIR, fname)
        if os.path.exists(fpath):
            s4.shapes.add_picture(fpath, x, y, Inches(3.7), Inches(2.25))

        # Caption underneath
        cap_box = s4.shapes.add_textbox(x, y + Inches(2.3), Inches(3.7), Inches(0.4))
        p = cap_box.text_frame.paragraphs[0]
        p.text = label
        p.alignment = PP_ALIGN.CENTER
        p.font.name = "Georgia"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = COLOR_BLACK

    # =========================================================================
    # SLIDE 5: IMPACT AND BENEFITS (Exact Reference Layout)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_white_bg(s5)
    add_common_header(s5, 5, "IMPACT AND BENEFITS")

    # Top Row: 3 Big Metric Cards
    metrics = [
        ("14", "Deterministic checks per record", COLOR_BLUE_TITLE),
        ("<200ms", "Measured validation time per 1,000 batch rows (test suite)", COLOR_BLUE_TITLE),
        ("44/44", "Automated pytest cases passing (100% test pass rate)", COLOR_BLUE_TITLE)
    ]
    for i, (num, desc, color) in enumerate(metrics):
        x = Inches(0.8 + i * 3.96)
        card = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(1.35), Inches(3.8), Inches(1.5))
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_LIGHT_BG
        card.line.color.rgb = COLOR_BORDER

        tb = s5.shapes.add_textbox(x + Inches(0.2), Inches(1.4), Inches(3.4), Inches(1.3))
        tf = tb.text_frame
        p1 = tf.paragraphs[0]
        p1.text = num
        p1.font.name = "Georgia"
        p1.font.size = Pt(36)
        p1.font.bold = True
        p1.font.color.rgb = color

        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.name = "Arial"
        p2.font.size = Pt(10.5)
        p2.font.color.rgb = COLOR_MUTED_TEXT

    # Middle Row: Stakeholder Impact
    sh_title = s5.shapes.add_textbox(Inches(0.8), Inches(3.0), Inches(5.0), Inches(0.4))
    p = sh_title.text_frame.paragraphs[0]
    p.text = "Stakeholder Impact"
    p.font.name = "Georgia"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLACK

    stakeholders = [
        ("👥  Colleges", [
            "Catch intake-capacity and duplicate roll number errors before formal submission.",
            "Clear completeness tracking (0% → 100%) and instant course quota allocation gauges."
        ]),
        ("👁️  Scrutiny Officers", [
            "Prioritized, explainable findings with transparent penalty scoring instead of raw diagnostics.",
            "14 checks collapsed into one actionable verdict (COMPLIANT / ISSUE FOUND)."
        ]),
        ("🛡️  Regulators & Employers", [
            "Every admission decision and third-party verification traceable via immutable audit trail.",
            "Instant 2-second QR verification eliminates paper credential fraud forever."
        ])
    ]
    for i, (stitle, sbullets) in enumerate(stakeholders):
        x = Inches(0.8 + i * 3.96)
        tb = s5.shapes.add_textbox(x, Inches(3.4), Inches(3.8), Inches(1.8))
        tf = tb.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = stitle
        p.font.name = "Georgia"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = COLOR_BLUE_TITLE

        for b in sbullets:
            p_b = tf.add_paragraph()
            p_b.text = f"•  {b}"
            p_b.font.name = "Arial"
            p_b.font.size = Pt(10)
            p_b.font.color.rgb = COLOR_MUTED_TEXT
            p_b.space_after = Pt(4)

    # Bottom Full-Width Dark Box: Governance Alignment & Data Sovereignty (Exact Reference)
    gov_card = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.35), Inches(11.7), Inches(1.65))
    gov_card.fill.solid()
    gov_card.fill.fore_color.rgb = COLOR_DARK_BOX
    gov_card.line.fill.background()

    tb_gov = s5.shapes.add_textbox(Inches(1.0), Inches(5.45), Inches(11.3), Inches(1.4))
    tf_g = tb_gov.text_frame
    tf_g.word_wrap = True

    p = tf_g.paragraphs[0]
    p.text = "🔒   Governance Alignment & Data Sovereignty"
    p.font.name = "Georgia"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE

    p2 = tf_g.add_paragraph()
    p2.text = 'Operationalizes NEP 2020 & AICTE Approval Process Handbook (APH 2026-27) — "Light but Tight" transparent, technology-enabled, single-window evaluation. All processing runs on deterministic mathematical logic with zero external AI API calls in the current implementation, so student records never leave the sovereign institutional environment. Final statutory decisions remain exclusively with authorized officers.'
    p2.font.name = "Arial"
    p2.font.size = Pt(10)
    p2.font.color.rgb = RGBColor(203, 213, 225)

    # =========================================================================
    # SLIDE 6: RESEARCH AND REFERENCES (Exact Reference Table)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_white_bg(s6)
    add_common_header(s6, 6, "RESEARCH AND REFERENCES")

    # Table Layout
    table_shape = s6.shapes.add_table(10, 3, Inches(0.8), Inches(1.35), Inches(11.7), Inches(5.6))
    table = table_shape.table

    # Column Widths
    table.columns[0].width = Inches(3.2)
    table.columns[1].width = Inches(5.5)
    table.columns[2].width = Inches(3.0)

    # Table Headers
    headers = ["Regulatory Body / Standard", "Citation & Mandate", "Official URL"]
    for col_idx, htext in enumerate(headers):
        cell = table.cell(0, col_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = COLOR_LIGHT_BG
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.text = htext
        p.font.name = "Georgia"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = COLOR_BLACK

    # Table Data Rows (Exact matching style)
    data_rows = [
        ("AICTE Official Portal", "All India Council for Technical Education national portal and approval gateway", "https://www.aicte-india.org"),
        ("AICTE Approval Process Handbook (APH 2026-27)", "Statutory criteria for approved intake limits, supernumerary quotas (TFW 5%, NRI 5%, FN 15%)", "AICTE Approval Process Bulletins"),
        ("AICTE Act No. 52 of 1987", "Statutory mandate for proper planning and coordinated development of technical education in India", "AICTE Act & History"),
        ("Smart India Hackathon (SIH 2026)", "Official portal for SIH national innovation and solution submissions", "https://sih.gov.in"),
        ("National Education Policy (NEP 2020)", "Section 18: Transforming the Regulatory System into an objective, single-window evaluation framework", "https://www.education.gov.in/nep"),
        ("APAAR / ABC Registry Mandate", "Ministry of Education 'One Nation, One Student ID' automated academic depository guidelines", "https://apaar.education.gov.in"),
        ("Digital India Initiative (MeitY)", "Ministry of Electronics and IT guidelines for e-Governance, paperless workflows, and e-signatures", "https://www.digitalindia.gov.in"),
        ("National Single Window System (NSWS)", "Integrated digital approval portal for statutory clearances in India", "https://www.nsws.gov.in"),
        ("DigiLocker National Verification", "National paperless credential and institutional document verification system", "https://www.digilocker.gov.in")
    ]

    for row_idx, (c0, c1, c2) in enumerate(data_rows, start=1):
        cell0 = table.cell(row_idx, 0)
        cell0.text = c0
        cell0.text_frame.paragraphs[0].font.name = "Arial"
        cell0.text_frame.paragraphs[0].font.size = Pt(9.5)
        cell0.text_frame.paragraphs[0].font.bold = True
        cell0.text_frame.paragraphs[0].font.color.rgb = COLOR_BLACK

        cell1 = table.cell(row_idx, 1)
        cell1.text = c1
        cell1.text_frame.paragraphs[0].font.name = "Arial"
        cell1.text_frame.paragraphs[0].font.size = Pt(9)
        cell1.text_frame.paragraphs[0].font.color.rgb = COLOR_MUTED_TEXT

        cell2 = table.cell(row_idx, 2)
        cell2.text = c2
        cell2.text_frame.paragraphs[0].font.name = "Arial"
        cell2.text_frame.paragraphs[0].font.size = Pt(9)
        cell2.text_frame.paragraphs[0].font.color.rgb = COLOR_BLUE_TITLE
        cell2.text_frame.paragraphs[0].font.underline = True

    out_file = r"c:\All_Projects\apaar-aicte-platform\SIH26263_Presentation.pptx"
    prs.save(out_file)
    print(f"Exact SIH reference PPT successfully created: {out_file}")

if __name__ == "__main__":
    build_presentation()

