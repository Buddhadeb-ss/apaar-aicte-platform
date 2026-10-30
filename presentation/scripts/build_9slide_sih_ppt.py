"""
SIH26263 — 9-Slide Premium Dark-Navy Presentation Builder
Team: Sentinels | Org: AICTE | Category: Software / Smart Automation

Design spec:
  Background:  #0B1220
  Card/panel:  #111C30
  Secondary:   #172554
  Accent cyan: #38BDF8
  Text white:  #F8FAFC
  Muted text:  #94A3B8
  Verified:    #34D399
  Warning:     #FBBF24
  Critical:    #FB7185
  Font:        Arial (Inter fallback not available in pptx without install)
"""

import sys
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from PIL import Image, ImageDraw, ImageFont
import io

# ─── Color palette ────────────────────────────────────────────────────────────
BG       = RGBColor(0x0B, 0x12, 0x20)
CARD     = RGBColor(0x11, 0x1C, 0x30)
CARD2    = RGBColor(0x17, 0x25, 0x54)
CYAN     = RGBColor(0x38, 0xBD, 0xF8)
WHITE    = RGBColor(0xF8, 0xFA, 0xFC)
MUTED    = RGBColor(0x94, 0xA3, 0xB8)
GREEN    = RGBColor(0x34, 0xD3, 0x99)
AMBER    = RGBColor(0xFB, 0xBF, 0x24)
CRIMSON  = RGBColor(0xFB, 0x71, 0x85)
DARKBG   = RGBColor(0x07, 0x0D, 0x18)

# ─── Slide size: 13.33" × 7.5" (standard widescreen 16:9) ────────────────────
W = Inches(13.33)
H = Inches(7.5)

ASSETS = r"c:\All_Projects\apaar-aicte-platform\presentation_assets"

def rgb_tuple(r):
    return (r[0], r[1], r[2])

# ─── PIL helpers ──────────────────────────────────────────────────────────────
def pil_img_to_stream(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def make_bg_image(w_px=1920, h_px=1080):
    """Dark navy background with subtle grid dots."""
    img = Image.new("RGB", (w_px, h_px), rgb_tuple(BG))
    draw = ImageDraw.Draw(img)
    dot_color = (0x16, 0x25, 0x40)
    for x in range(0, w_px, 40):
        for y in range(0, h_px, 40):
            draw.ellipse([x-1, y-1, x+1, y+1], fill=dot_color)
    # subtle horizontal accent line at ~15% from top
    draw.rectangle([0, int(h_px*0.14), w_px, int(h_px*0.145)], fill=(0x0F, 0x1E, 0x38))
    return img


def make_cover_bg(w_px=1920, h_px=1080):
    """Cover with gradient sweep and subtle grid."""
    img = make_bg_image(w_px, h_px)
    draw = ImageDraw.Draw(img)
    # Left accent stripe
    for i in range(6):
        alpha = max(0, 60 - i*10)
        c = (0x38, 0xBD, 0xF8)
        draw.rectangle([int(w_px*0.0), 0, int(w_px*0.003)+i*2, h_px],
                       fill=(c[0]//4, c[1]//4, c[2]//4))
    # bottom strip
    draw.rectangle([0, h_px-4, w_px, h_px], fill=(0x38, 0xBD, 0xF8))
    return img


# ─── python-pptx helpers ──────────────────────────────────────────────────────
def add_bg(slide, img_stream, prs_width, prs_height):
    pic = slide.shapes.add_picture(img_stream, 0, 0, prs_width, prs_height)
    slide.shapes._spTree.remove(pic._element)
    slide.shapes._spTree.insert(2, pic._element)


def add_rect(slide, left, top, width, height, fill_color, alpha=None, line_color=None, line_width=Pt(0)):
    from pptx.util import Emu
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        left, top, width, height
    )
    shape.line.width = line_width
    if line_color:
        shape.line.color.rgb = line_color
        shape.line.width = line_width if line_width else Pt(1)
    else:
        shape.line.fill.background()
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    return shape


def add_text_box(slide, text, left, top, width, height,
                 font_size=Pt(18), bold=False, color=WHITE,
                 align=PP_ALIGN.LEFT, italic=False, wrap=True):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = font_size
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = "Arial"
    return txBox


def add_text_box_multiline(slide, lines, left, top, width, height,
                            font_size=Pt(16), bold=False, color=WHITE,
                            align=PP_ALIGN.LEFT, line_spacing=None):
    """lines: list of (text, bold, color, font_size) tuples"""
    from pptx.util import Pt as _Pt
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    first = True
    for item in lines:
        if isinstance(item, str):
            txt, b, c, fs = item, bold, color, font_size
        else:
            txt, b, c, fs = item[0], item[1], item[2], item[3]
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.alignment = align
        if line_spacing:
            p.line_spacing = line_spacing
        run = p.add_run()
        run.text = txt
        run.font.size = fs
        run.font.bold = b
        run.font.color.rgb = c
        run.font.name = "Arial"
    return txBox


def add_image(slide, path, left, top, width, height):
    if os.path.exists(path):
        return slide.shapes.add_picture(path, left, top, width, height)
    return None


def add_card(slide, left, top, width, height, fill=CARD, border=None, border_width=Pt(1)):
    r = add_rect(slide, left, top, width, height, fill,
                 line_color=border, line_width=border_width)
    return r


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def slide1_cover(prs):
    """Cover: TRUST EVERY RECORD. VERIFY EVERY ENROLMENT."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank

    # Background
    bg = make_cover_bg(1920, 1080)
    add_bg(slide, pil_img_to_stream(bg), W, H)

    # Top-left cyan accent bar
    add_rect(slide, 0, 0, Inches(0.06), H, CYAN)

    # AICTE label top-right
    add_text_box(slide, "AICTE  ·  SMART INDIA HACKATHON 2026",
                 Inches(7.5), Inches(0.22), Inches(5.5), Inches(0.4),
                 font_size=Pt(11), color=MUTED, align=PP_ALIGN.RIGHT)

    # PS label
    add_text_box(slide, "PS: SIH26263",
                 Inches(7.5), Inches(0.58), Inches(5.5), Inches(0.35),
                 font_size=Pt(11), color=CYAN, align=PP_ALIGN.RIGHT, bold=True)

    # Big headline
    add_text_box(slide, "TRUST EVERY RECORD.",
                 Inches(0.9), Inches(1.5), Inches(11.5), Inches(1.2),
                 font_size=Pt(46), bold=True, color=WHITE)
    add_text_box(slide, "VERIFY EVERY ENROLMENT.",
                 Inches(0.9), Inches(2.55), Inches(11.5), Inches(1.2),
                 font_size=Pt(46), bold=True, color=CYAN)

    # Subtitle
    add_text_box(slide,
                 "APAAR-Linked Student Data Integrity & Verification Platform\n"
                 "for AICTE-Approved Institutions",
                 Inches(0.9), Inches(3.75), Inches(9.5), Inches(0.9),
                 font_size=Pt(18), color=MUTED)

    # Divider line
    from pptx.util import Pt as _Pt
    ln = slide.shapes.add_connector(1, Inches(0.9), Inches(4.72), Inches(12.4), Inches(4.72))
    ln.line.color.rgb = CYAN
    ln.line.width = Pt(1)

    # Bottom meta strip card
    add_card(slide, Inches(0.9), Inches(4.9), Inches(11.5), Inches(0.7), fill=CARD2)
    meta_lines = [
        ("Team: Sentinels", False, WHITE, Pt(13)),
    ]
    add_text_box(slide,
                 "Team: Sentinels   ·   Category: Software / Smart Automation   ·   Organisation: AICTE",
                 Inches(1.1), Inches(5.0), Inches(9.0), Inches(0.5),
                 font_size=Pt(13), color=MUTED)

    # Working model thumbnails row (small, bottom)
    wm_files = ["wm_01_login.png","wm_02_college_portal.png","wm_03_command_center.png",
                "wm_04_collision.png","wm_05_workbench.png","wm_06_qr_verify.png"]
    thumb_w = Inches(1.65)
    thumb_h = Inches(1.0)
    start_x = Inches(0.9)
    gap = Inches(0.18)
    for i, wm in enumerate(wm_files):
        path = os.path.join(ASSETS, wm)
        if os.path.exists(path):
            x = start_x + i * (thumb_w + gap)
            add_card(slide, x, Inches(5.8), thumb_w, thumb_h, fill=CARD, border=CYAN, border_width=Pt(0.75))
            add_image(slide, path, x + Inches(0.02), Inches(5.82), thumb_w - Inches(0.04), thumb_h - Inches(0.04))


def slide2_problem(prs):
    """The Problem: 4 pain points."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = make_bg_image()
    add_bg(slide, pil_img_to_stream(bg), W, H)
    add_rect(slide, 0, 0, Inches(0.06), H, CYAN)

    # Slide label
    add_text_box(slide, "THE PROBLEM", Inches(0.9), Inches(0.25), Inches(6), Inches(0.4),
                 font_size=Pt(11), color=CYAN, bold=True)

    # Headline
    add_text_box(slide, "Student records that can't be trusted.",
                 Inches(0.9), Inches(0.55), Inches(10), Inches(0.8),
                 font_size=Pt(32), bold=True, color=WHITE)

    add_text_box(slide,
                 "Institutions across India submit enrolment data through disconnected, manual processes\n"
                 "with no unified validation, no duplicate detection and no real-time oversight.",
                 Inches(0.9), Inches(1.3), Inches(10.5), Inches(0.75),
                 font_size=Pt(16), color=MUTED)

    # 4 problem cards 2×2
    problems = [
        (AMBER,  "No Cross-Institution Visibility",
                 "A student can hold active enrolments at multiple institutions simultaneously "
                 "with no automated detection or flag."),
        (CRIMSON,"Manual Data Collection Gaps",
                 "APAAR IDs, programme codes and enrolment details arrive in inconsistent formats "
                 "across institutions — no field-level validation enforced."),
        (CRIMSON,"Intake Monitoring Blind Spot",
                 "Institutions may exceed approved intake limits without triggering any regulatory alert, "
                 "distorting official enrolment figures."),
        (AMBER,  "No Authorised Verification Channel",
                 "Employers and admissions teams have no trusted, privacy-respecting way to verify "
                 "whether a credential is backed by a valid enrolment record."),
    ]

    cols = 2
    card_w = Inches(5.8)
    card_h = Inches(1.85)
    col_gap = Inches(0.35)
    row_gap = Inches(0.22)
    start_x = Inches(0.9)
    start_y = Inches(2.2)

    for i, (accent, title, desc) in enumerate(problems):
        col = i % cols
        row = i // cols
        x = start_x + col * (card_w + col_gap)
        y = start_y + row * (card_h + row_gap)
        add_card(slide, x, y, card_w, card_h, fill=CARD, border=accent, border_width=Pt(1.5))
        # Accent top stripe
        add_rect(slide, x, y, card_w, Inches(0.045), accent)
        # Title
        add_text_box(slide, title,
                     x + Inches(0.2), y + Inches(0.15), card_w - Inches(0.3), Inches(0.45),
                     font_size=Pt(15), bold=True, color=WHITE)
        # Desc
        add_text_box(slide, desc,
                     x + Inches(0.2), y + Inches(0.6), card_w - Inches(0.3), Inches(1.1),
                     font_size=Pt(13), color=MUTED)

    # Bottom disclaimer
    add_text_box(slide, "No external statistics cited — observations based on domain analysis of the problem statement.",
                 Inches(0.9), Inches(6.9), Inches(11.5), Inches(0.4),
                 font_size=Pt(10), color=MUTED, italic=True)


def slide3_solution(prs):
    """Our Solution: 6-stage pipeline."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = make_bg_image()
    add_bg(slide, pil_img_to_stream(bg), W, H)
    add_rect(slide, 0, 0, Inches(0.06), H, CYAN)

    add_text_box(slide, "OUR SOLUTION", Inches(0.9), Inches(0.25), Inches(6), Inches(0.4),
                 font_size=Pt(11), color=CYAN, bold=True)
    add_text_box(slide, "A Validation-First Enrolment Platform.",
                 Inches(0.9), Inches(0.55), Inches(10), Inches(0.75),
                 font_size=Pt(32), bold=True, color=WHITE)

    # 6-stage pipeline
    stages = [
        ("01", "Institution\nSubmission", "CSV upload\nor manual entry"),
        ("02", "Server-Side\nValidation", "14 deterministic\nstatutory rules"),
        ("03", "Issue Review\n& Correction", "Flagged rows,\nerror report"),
        ("04", "Central\nRegistry", "Canonical student\nidentity store"),
        ("05", "AICTE\nAnalytics", "Intake, duplicates,\ncompliance"),
        ("06", "Authorised\nVerification", "Role-gated QR\ncredential check"),
    ]

    n = len(stages)
    box_w = Inches(1.78)
    box_h = Inches(1.55)
    gap = Inches(0.18)
    arrow_w = Inches(0.18)
    total_w = n * box_w + (n-1) * (gap + arrow_w)
    start_x = (W - total_w) / 2
    stage_y = Inches(1.7)

    for i, (num, title, sub) in enumerate(stages):
        x = start_x + i * (box_w + gap + arrow_w)
        # Box
        fill = CARD2 if i in (1,2,4,5) else CARD
        add_card(slide, x, stage_y, box_w, box_h, fill=fill, border=CYAN, border_width=Pt(1))
        # Top number badge
        add_text_box(slide, num, x + Inches(0.08), stage_y + Inches(0.1), Inches(0.5), Inches(0.35),
                     font_size=Pt(11), bold=True, color=CYAN)
        # Stage title
        add_text_box(slide, title,
                     x + Inches(0.1), stage_y + Inches(0.38), box_w - Inches(0.15), Inches(0.75),
                     font_size=Pt(13), bold=True, color=WHITE)
        # Sub-text
        add_text_box(slide, sub,
                     x + Inches(0.1), stage_y + Inches(1.1), box_w - Inches(0.15), Inches(0.45),
                     font_size=Pt(10.5), color=MUTED)
        # Arrow (except last)
        if i < n-1:
            ax = x + box_w + gap * 0.15
            ay = stage_y + box_h/2 - Inches(0.03)
            ln = slide.shapes.add_connector(1, ax, ay, ax + arrow_w + gap*0.7, ay)
            ln.line.color.rgb = CYAN
            ln.line.width = Pt(1.5)

    # Key feature pills below
    features = [
        (GREEN,  "✓ Zero-trust validation\nbefore commit"),
        (CYAN,   "⬡ Stable UUID per\nstudent identity"),
        (CYAN,   "⬡ Role-based access\nfor 5 user types"),
        (AMBER,  "⚑ Cross-institution\nduplicate detection"),
        (GREEN,  "✓ Signed verifiable\ncredential pass"),
    ]

    pill_w = Inches(2.3)
    pill_h = Inches(0.95)
    pill_gap = Inches(0.2)
    pill_total = len(features) * pill_w + (len(features)-1) * pill_gap
    pill_x = (W - pill_total) / 2
    pill_y = Inches(3.65)

    for i, (color, text) in enumerate(features):
        px = pill_x + i * (pill_w + pill_gap)
        add_card(slide, px, pill_y, pill_w, pill_h, fill=CARD, border=color, border_width=Pt(1))
        add_text_box(slide, text, px + Inches(0.15), pill_y + Inches(0.12),
                     pill_w - Inches(0.2), pill_h - Inches(0.1),
                     font_size=Pt(12), color=WHITE)

    # Live product peek: 3 hero screenshots at bottom
    screens = [
        ("hero_command_center.png", "AICTE Dashboard"),
        ("hero_validation_workbench.png", "Validation Workbench"),
        ("hero_student_pass.png", "Credential Pass"),
    ]
    sc_w = Inches(3.7)
    sc_h = Inches(1.85)
    sc_gap = Inches(0.4)
    sc_total = len(screens) * sc_w + (len(screens)-1) * sc_gap
    sc_x = (W - sc_total) / 2
    sc_y = Inches(4.82)

    for i, (fname, label) in enumerate(screens):
        sx = sc_x + i * (sc_w + sc_gap)
        add_card(slide, sx, sc_y, sc_w, sc_h, fill=CARD, border=CYAN, border_width=Pt(0.75))
        path = os.path.join(ASSETS, fname)
        if os.path.exists(path):
            add_image(slide, path, sx + Inches(0.04), sc_y + Inches(0.04),
                      sc_w - Inches(0.08), sc_h - Inches(0.3))
        add_text_box(slide, label, sx, sc_y + sc_h - Inches(0.28), sc_w, Inches(0.28),
                     font_size=Pt(9.5), color=MUTED, align=PP_ALIGN.CENTER)


def slide4_differentiators(prs):
    """What Makes It Different: 2-col comparison."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = make_bg_image()
    add_bg(slide, pil_img_to_stream(bg), W, H)
    add_rect(slide, 0, 0, Inches(0.06), H, CYAN)

    add_text_box(slide, "DIFFERENTIATION", Inches(0.9), Inches(0.25), Inches(6), Inches(0.4),
                 font_size=Pt(11), color=CYAN, bold=True)
    add_text_box(slide, "Validation-first, not collection-first.",
                 Inches(0.9), Inches(0.55), Inches(11), Inches(0.75),
                 font_size=Pt(32), bold=True, color=WHITE)

    # Column headers
    col_l_x = Inches(0.9)
    col_r_x = Inches(7.0)
    col_w = Inches(5.85)
    header_y = Inches(1.55)

    add_card(slide, col_l_x, header_y, col_w, Inches(0.55), fill=RGBColor(0x2D, 0x0A, 0x0A))
    add_text_box(slide, "✗  Conventional Record Collection",
                 col_l_x + Inches(0.2), header_y + Inches(0.1), col_w - Inches(0.3), Inches(0.4),
                 font_size=Pt(14), bold=True, color=CRIMSON)

    add_card(slide, col_r_x, header_y, col_w, Inches(0.55), fill=RGBColor(0x05, 0x20, 0x14))
    add_text_box(slide, "✓  Our Validation-First Workflow",
                 col_r_x + Inches(0.2), header_y + Inches(0.1), col_w - Inches(0.3), Inches(0.4),
                 font_size=Pt(14), bold=True, color=GREEN)

    rows = [
        ("Identity vs Enrolment",
         "Student identity conflated with enrolment — no distinction between who the student is and what they are enrolled in.",
         "Stable internal UUID separates student identity from enrolment records. Multiple enrolments tracked independently."),
        ("Duplicate Detection",
         "No automated cross-institution check. Duplicate enrolments may persist undetected across academic years.",
         "Normalised exact-match detection flags duplicate APAAR IDs within and across institutions before record commit."),
        ("Intake Accounting",
         "Manual count of admitted students with no separation of ordinary and supernumerary seats.",
         "Active enrolment count, grouped by institution, programme and year. Supernumerary seats tracked separately."),
        ("Access Control",
         "Flat access model — most users can view or edit all records.",
         "Role-based access for 5 roles: AICTE Admin, Institution Admin, Operator, Student Viewer, Authorised Verifier."),
    ]

    row_h = Inches(1.05)
    row_y = Inches(2.22)
    row_gap = Inches(0.08)

    for i, (label, left_text, right_text) in enumerate(rows):
        y = row_y + i * (row_h + row_gap)
        # Label strip
        add_rect(slide, col_l_x, y, Inches(11.95), Inches(0.28), CARD2)
        add_text_box(slide, label,
                     col_l_x + Inches(0.15), y + Inches(0.05), Inches(11.5), Inches(0.22),
                     font_size=Pt(11), bold=True, color=CYAN)
        # Left cell
        add_card(slide, col_l_x, y + Inches(0.28), col_w, row_h - Inches(0.28),
                 fill=RGBColor(0x15, 0x08, 0x0C), border=RGBColor(0x40, 0x15, 0x20), border_width=Pt(0.5))
        add_text_box(slide, left_text,
                     col_l_x + Inches(0.15), y + Inches(0.33), col_w - Inches(0.25), row_h - Inches(0.38),
                     font_size=Pt(12), color=MUTED)
        # Right cell
        add_card(slide, col_r_x, y + Inches(0.28), col_w, row_h - Inches(0.28),
                 fill=RGBColor(0x04, 0x17, 0x0E), border=RGBColor(0x10, 0x3D, 0x26), border_width=Pt(0.5))
        add_text_box(slide, right_text,
                     col_r_x + Inches(0.15), y + Inches(0.33), col_w - Inches(0.25), row_h - Inches(0.38),
                     font_size=Pt(12), color=WHITE)


def slide5_architecture(prs):
    """Technical Architecture."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = make_bg_image()
    add_bg(slide, pil_img_to_stream(bg), W, H)
    add_rect(slide, 0, 0, Inches(0.06), H, CYAN)

    add_text_box(slide, "TECHNICAL ARCHITECTURE", Inches(0.9), Inches(0.25), Inches(6), Inches(0.4),
                 font_size=Pt(11), color=CYAN, bold=True)
    add_text_box(slide, "Modular, role-aware, audit-logged.",
                 Inches(0.9), Inches(0.55), Inches(10), Inches(0.75),
                 font_size=Pt(30), bold=True, color=WHITE)

    # Three-column layout: Frontend | Backend Services | Data & Future
    col_w = Inches(3.6)
    col_h = Inches(5.1)
    col_gap = Inches(0.4)
    col_y = Inches(1.5)

    # Column 1: Frontend
    c1x = Inches(0.9)
    add_card(slide, c1x, col_y, col_w, col_h, fill=CARD, border=CYAN, border_width=Pt(1))
    add_text_box(slide, "CLIENT TIER", c1x + Inches(0.2), col_y + Inches(0.12),
                 col_w - Inches(0.3), Inches(0.35), font_size=Pt(10), bold=True, color=CYAN)
    client_items = [
        ("React 18 + TypeScript", WHITE, Pt(13), True),
        ("Vite build pipeline", MUTED, Pt(12), False),
        ("5-role adaptive UI", WHITE, Pt(13), True),
        ("AICTE Command Centre", MUTED, Pt(12), False),
        ("Institution Portal", MUTED, Pt(12), False),
        ("Student Credential Pass", MUTED, Pt(12), False),
        ("Validation Workbench", MUTED, Pt(12), False),
        ("Bulk Upload Wizard", MUTED, Pt(12), False),
    ]
    for j, (txt, col, fs, b) in enumerate(client_items):
        yy = col_y + Inches(0.58) + j * Inches(0.49)
        add_text_box(slide, ("▸ " if not b else "■ ") + txt,
                     c1x + Inches(0.15), yy, col_w - Inches(0.25), Inches(0.44),
                     font_size=fs, color=col, bold=b)

    # Column 2: Backend
    c2x = c1x + col_w + col_gap
    add_card(slide, c2x, col_y, col_w, col_h, fill=CARD, border=CYAN, border_width=Pt(1))
    add_text_box(slide, "APPLICATION TIER", c2x + Inches(0.2), col_y + Inches(0.12),
                 col_w - Inches(0.3), Inches(0.35), font_size=Pt(10), bold=True, color=CYAN)
    backend_items = [
        ("FastAPI (Python)", WHITE, Pt(13), True),
        ("JWT authentication + RBAC", MUTED, Pt(12), False),
        ("Bcrypt password hashing", MUTED, Pt(12), False),
        ("Validation Engine", WHITE, Pt(13), True),
        ("14 deterministic rules", AMBER, Pt(12), False),
        ("NOT ML / not AI", MUTED, Pt(11), False),
        ("Credential Signing Service", WHITE, Pt(13), True),
        ("QR-linked verifiable pass", MUTED, Pt(12), False),
        ("Audit Event Logger", WHITE, Pt(13), True),
        ("No PII in logs", GREEN, Pt(12), False),
    ]
    for j, (txt, col, fs, b) in enumerate(backend_items):
        yy = col_y + Inches(0.58) + j * Inches(0.44)
        prefix = "■ " if b else "▸ "
        add_text_box(slide, prefix + txt,
                     c2x + Inches(0.15), yy, col_w - Inches(0.25), Inches(0.42),
                     font_size=fs, color=col, bold=b)

    # Column 3: Data + Future
    c3x = c2x + col_w + col_gap
    # Data layer box
    data_h = Inches(2.3)
    add_card(slide, c3x, col_y, col_w, data_h, fill=CARD, border=CYAN, border_width=Pt(1))
    add_text_box(slide, "DATA TIER", c3x + Inches(0.2), col_y + Inches(0.12),
                 col_w - Inches(0.3), Inches(0.35), font_size=Pt(10), bold=True, color=CYAN)
    data_items = [
        ("SQLAlchemy ORM", WHITE, Pt(13), True),
        ("SQLite  ←  PROTOTYPE ONLY", AMBER, Pt(11), False),
        ("Not for production deployment", MUTED, Pt(10), False),
        ("Alembic migrations", MUTED, Pt(12), False),
        ("13 normalised tables", MUTED, Pt(12), False),
    ]
    for j, (txt, col, fs, b) in enumerate(data_items):
        yy = col_y + Inches(0.55) + j * Inches(0.36)
        add_text_box(slide, ("■ " if b else "▸ ") + txt,
                     c3x + Inches(0.15), yy, col_w - Inches(0.25), Inches(0.35),
                     font_size=fs, color=col, bold=b)

    # Future integration box (dashed border via amber)
    future_y = col_y + data_h + Inches(0.22)
    future_h = col_h - data_h - Inches(0.22)
    add_card(slide, c3x, future_y, col_w, future_h, fill=RGBColor(0x11, 0x16, 0x20),
             border=AMBER, border_width=Pt(1))
    add_text_box(slide, "FUTURE INTEGRATION", c3x + Inches(0.2), future_y + Inches(0.1),
                 col_w - Inches(0.3), Inches(0.35), font_size=Pt(10), bold=True, color=AMBER)
    add_text_box(slide,
                 "PLANNED — NOT ACTIVE\n\n"
                 "▸ APAAR Registry API\n"
                 "▸ DigiLocker credential sync\n"
                 "▸ National Academic Depository\n"
                 "▸ Production PostgreSQL\n\n"
                 "Subject to AICTE authorisation.",
                 c3x + Inches(0.15), future_y + Inches(0.5), col_w - Inches(0.25), future_h - Inches(0.55),
                 font_size=Pt(11), color=MUTED)

    # Tech stack grid image (bottom row)
    tech_path = os.path.join(ASSETS, "tech_stack_grid.png")
    if os.path.exists(tech_path):
        add_image(slide, tech_path, c1x, Inches(6.72), Inches(7.5), Inches(0.55))


def slide6_validation(prs):
    """Automated Validation Engine."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = make_bg_image()
    add_bg(slide, pil_img_to_stream(bg), W, H)
    add_rect(slide, 0, 0, Inches(0.06), H, CYAN)

    add_text_box(slide, "VALIDATION ENGINE", Inches(0.9), Inches(0.25), Inches(6), Inches(0.4),
                 font_size=Pt(11), color=CYAN, bold=True)
    add_text_box(slide, "14 deterministic statutory rules. No ML. No guesswork.",
                 Inches(0.9), Inches(0.55), Inches(11), Inches(0.75),
                 font_size=Pt(28), bold=True, color=WHITE)

    # 6-step pipeline banner
    steps = ["Upload", "Parse", "Validate", "Categorise", "Review", "Commit / Reject"]
    step_w = Inches(1.95)
    step_h = Inches(0.52)
    step_gap = Inches(0.06)
    step_x = Inches(0.9)
    step_y = Inches(1.5)
    for i, s in enumerate(steps):
        sx = step_x + i * (step_w + step_gap)
        col = CYAN if i in (2, 3) else CARD2
        add_card(slide, sx, step_y, step_w, step_h, fill=col, border=CYAN, border_width=Pt(0.75))
        add_text_box(slide, s, sx, step_y + Inches(0.1), step_w, Inches(0.38),
                     font_size=Pt(12), bold=True,
                     color=DARKBG if i in (2, 3) else WHITE,
                     align=PP_ALIGN.CENTER)
        if i < len(steps)-1:
            ax = sx + step_w + step_gap*0.1
            ay = step_y + step_h/2
            ln = slide.shapes.add_connector(1, ax, ay, ax + step_gap*0.9, ay)
            ln.line.color.rgb = CYAN
            ln.line.width = Pt(1)

    # Issue table
    tbl_x = Inches(0.9)
    tbl_y = Inches(2.25)
    tbl_w = Inches(11.5)
    col_widths = [Inches(1.5), Inches(2.1), Inches(1.4), Inches(1.1), Inches(4.4), Inches(1.0)]
    headers = ["Row", "Student ID", "Rule", "Severity", "Finding", "Status"]

    table_rows = [
        ("1", "STU-AIT-0012", "—", "—", "All mandatory fields present. APAAR format valid.", "PASS"),
        ("2", "STU-AIT-0017", "R-02", "CRITICAL", "APAAR ID 'APAAR-X-99' does not match configured format pattern.", "FLAG"),
        ("3", "STU-BCN-0031", "R-03", "CRITICAL", "APAAR 550011223344 already linked to STU-AIT-0009 in this institution.", "FLAG"),
        ("4", "STU-AIT-0024", "R-06", "CRITICAL", "programme_code is missing — required field for enrolment record.", "FLAG"),
        ("5", "STU-AIT-0033", "R-09", "HIGH", "Accepting this row would bring CS active enrolment to 122 vs intake 120.", "FLAG"),
    ]

    status_colors = {"PASS": GREEN, "FLAG": CRIMSON}
    severity_colors = {"CRITICAL": CRIMSON, "HIGH": AMBER, "—": MUTED}

    # Table header row
    row_h_hdr = Inches(0.42)
    for ci, (hdr, cw) in enumerate(zip(headers, col_widths)):
        cx = tbl_x + sum(col_widths[:ci])
        add_card(slide, cx, tbl_y, cw, row_h_hdr, fill=CARD2, border=CYAN, border_width=Pt(0.5))
        add_text_box(slide, hdr, cx + Inches(0.07), tbl_y + Inches(0.1), cw - Inches(0.1), Inches(0.3),
                     font_size=Pt(11), bold=True, color=CYAN, align=PP_ALIGN.LEFT)

    row_h_data = Inches(0.7)
    for ri, row_data in enumerate(table_rows):
        ry = tbl_y + row_h_hdr + ri * row_h_data
        bg_fill = CARD if ri % 2 == 0 else RGBColor(0x0D, 0x18, 0x2A)
        for ci, (val, cw) in enumerate(zip(row_data, col_widths)):
            cx = tbl_x + sum(col_widths[:ci])
            hdr = headers[ci]
            add_card(slide, cx, ry, cw, row_h_data, fill=bg_fill,
                     border=RGBColor(0x1E, 0x30, 0x4A), border_width=Pt(0.25))
            # Color logic
            if hdr == "Status":
                col = status_colors.get(val, WHITE)
                b = True
            elif hdr == "Severity":
                col = severity_colors.get(val, WHITE)
                b = val in ("CRITICAL", "HIGH")
            else:
                col = WHITE if hdr in ("Row","Student ID","Rule") else MUTED
                b = False
            add_text_box(slide, val, cx + Inches(0.07), ry + Inches(0.1), cw - Inches(0.1), row_h_data - Inches(0.15),
                         font_size=Pt(11), color=col, bold=b)

    # Validation workbench screenshot
    wb_path = os.path.join(ASSETS, "hero_validation_workbench.png")
    if os.path.exists(wb_path):
        add_image(slide, wb_path, Inches(0.9), Inches(6.05), Inches(5.0), Inches(1.18))
        add_text_box(slide, "Validation Workbench — live application screenshot",
                     Inches(0.9), Inches(7.1), Inches(5.0), Inches(0.3),
                     font_size=Pt(9), color=MUTED, italic=True)

    # Synthetic data label
    add_rect(slide, Inches(6.1), Inches(6.05), Inches(6.3), Inches(0.55), CARD2)
    add_text_box(slide,
                 "⚠  SYNTHETIC DEMONSTRATION DATA — Not sourced from official APAAR registry.\n"
                 "Format validation checks structure only; does not confirm registry authenticity.",
                 Inches(6.2), Inches(6.05), Inches(6.1), Inches(0.65),
                 font_size=Pt(9.5), color=AMBER, italic=True)


def slide7_live_product(prs):
    """Live Product: 4-panel screenshot grid."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = make_bg_image()
    add_bg(slide, pil_img_to_stream(bg), W, H)
    add_rect(slide, 0, 0, Inches(0.06), H, CYAN)

    add_text_box(slide, "LIVE PRODUCT", Inches(0.9), Inches(0.25), Inches(6), Inches(0.4),
                 font_size=Pt(11), color=CYAN, bold=True)
    add_text_box(slide, "From institutional submissions to regulatory intelligence.",
                 Inches(0.9), Inches(0.55), Inches(11), Inches(0.75),
                 font_size=Pt(28), bold=True, color=WHITE)

    screens = [
        ("hero_command_center.png", "AICTE National Command Centre",
         "KPI cards • cross-institution duplicates • intake alerts"),
        ("hero_institution_portal.png", "Institution Intake Dashboard",
         "Programme gauges • enrolment status • completeness"),
        ("hero_validation_workbench.png", "14-Rule Validation Workbench",
         "Issue codes • severity • row-level error export"),
        ("hero_student_pass.png", "Student Verifiable Credential Pass",
         "Masked APAAR • signed QR • role-gated visibility"),
    ]

    sc_w = Inches(5.85)
    sc_h = Inches(2.6)
    col_gap = Inches(0.35)
    row_gap = Inches(0.22)
    start_x = Inches(0.9)
    start_y = Inches(1.52)
    label_h = Inches(0.62)

    for i, (fname, title, caption) in enumerate(screens):
        col = i % 2
        row = i // 2
        x = start_x + col * (sc_w + col_gap)
        y = start_y + row * (sc_h + label_h + row_gap)

        # Card
        add_card(slide, x, y, sc_w, sc_h + label_h, fill=CARD, border=CYAN, border_width=Pt(1))

        # Screenshot
        path = os.path.join(ASSETS, fname)
        if os.path.exists(path):
            add_image(slide, path, x + Inches(0.04), y + Inches(0.04),
                      sc_w - Inches(0.08), sc_h - Inches(0.04))

        # Label strip
        add_rect(slide, x, y + sc_h, sc_w, label_h, CARD2)
        add_text_box(slide, title,
                     x + Inches(0.15), y + sc_h + Inches(0.05), sc_w - Inches(0.2), Inches(0.32),
                     font_size=Pt(12), bold=True, color=WHITE)
        add_text_box(slide, caption,
                     x + Inches(0.15), y + sc_h + Inches(0.34), sc_w - Inches(0.2), Inches(0.3),
                     font_size=Pt(10), color=MUTED)

    # Demo persona strip
    add_text_box(slide, "Demo personas: admin@aicte.gov.in  ·  registrar@apex.edu  ·  verifier@tcs.com  ·  student@apex.edu",
                 Inches(0.9), Inches(7.1), Inches(11.5), Inches(0.3),
                 font_size=Pt(10), color=MUTED, italic=True, align=PP_ALIGN.CENTER)


def slide8_security(prs):
    """Security, Verification & Measured Impact."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = make_bg_image()
    add_bg(slide, pil_img_to_stream(bg), W, H)
    add_rect(slide, 0, 0, Inches(0.06), H, CYAN)

    add_text_box(slide, "SECURITY & IMPACT", Inches(0.9), Inches(0.25), Inches(6), Inches(0.4),
                 font_size=Pt(11), color=CYAN, bold=True)
    add_text_box(slide, "Built for trust. Measured against real data.",
                 Inches(0.9), Inches(0.55), Inches(10), Inches(0.75),
                 font_size=Pt(30), bold=True, color=WHITE)

    # Left column: Security
    col_w = Inches(5.55)
    col_h = Inches(5.3)
    lx = Inches(0.9)
    rx = Inches(6.85)
    cy = Inches(1.5)

    add_card(slide, lx, cy, col_w, col_h, fill=CARD, border=CYAN, border_width=Pt(1))
    add_text_box(slide, "SECURITY DESIGN", lx + Inches(0.2), cy + Inches(0.12),
                 col_w - Inches(0.3), Inches(0.35), font_size=Pt(11), bold=True, color=CYAN)

    security_items = [
        (GREEN, "Role-Based Access Control", "5 distinct roles. Permissions enforced at API level on every endpoint."),
        (GREEN, "Tenant Isolation", "All queries scoped to institution. Cross-institution access requires AICTE role."),
        (CYAN,  "Masked APAAR Display", "APAAR ID shown as ****-****-3344 to operators. Full value to authorised roles only."),
        (CYAN,  "Signed Credential + QR", "Verifiable credential pass with signed metadata. QR links to role-gated verification endpoint."),
        (AMBER, "Audit Event Log", "All create, update and delete actions logged with actor, timestamp and change. No PII in log fields."),
        (GREEN, "Bcrypt + JWT", "Passwords hashed with bcrypt. Session tokens signed with configurable secret via environment variable."),
    ]

    for j, (accent, title, desc) in enumerate(security_items):
        iy = cy + Inches(0.58) + j * Inches(0.75)
        add_rect(slide, lx + Inches(0.2), iy + Inches(0.12), Inches(0.06), Inches(0.36), accent)
        add_text_box(slide, title,
                     lx + Inches(0.4), iy + Inches(0.08), col_w - Inches(0.55), Inches(0.3),
                     font_size=Pt(12), bold=True, color=WHITE)
        add_text_box(slide, desc,
                     lx + Inches(0.4), iy + Inches(0.37), col_w - Inches(0.55), Inches(0.35),
                     font_size=Pt(11), color=MUTED)

    # Right column: Impact metrics
    right_col_w = Inches(5.55)
    add_card(slide, rx, cy, right_col_w, col_h, fill=CARD, border=GREEN, border_width=Pt(1))
    add_text_box(slide, "SYSTEM MEASUREMENTS  (synthetic demo environment)",
                 rx + Inches(0.2), cy + Inches(0.12), right_col_w - Inches(0.3), Inches(0.4),
                 font_size=Pt(10), bold=True, color=GREEN)

    metrics = [
        (CRIMSON, "21", "Validation issues detected", "CRITICAL: 17 · HIGH: 2 · MEDIUM: 2"),
        (AMBER,   "1",  "Cross-institution collision candidate", "Vikram Malhotra — concurrent seats at 2 colleges"),
        (CYAN,    "44/44", "Pytest tests passing", "Full backend test suite · 0 failures"),
        (GREEN,   "100%", "Data completeness (demo data)", "All required fields populated in synthetic dataset"),
        (WHITE,   "3", "Demo institutions loaded", "Apex · Beacon · Zenith — 600 seats approved intake"),
        (WHITE,   "17", "Active enrolment records", "16 unique student identities · 1 duplicate enrolment"),
    ]

    for j, (accent, value, label, sub) in enumerate(metrics):
        my = cy + Inches(0.65) + j * Inches(0.75)
        add_rect(slide, rx + Inches(0.2), my, col_w - Inches(0.35), Inches(0.65), RGBColor(0x0A, 0x14, 0x24))
        add_text_box(slide, value,
                     rx + Inches(0.3), my + Inches(0.04), Inches(1.1), Inches(0.38),
                     font_size=Pt(22), bold=True, color=accent)
        add_text_box(slide, label,
                     rx + Inches(1.45), my + Inches(0.04), right_col_w - Inches(1.6), Inches(0.28),
                     font_size=Pt(12), bold=True, color=WHITE)
        add_text_box(slide, sub,
                     rx + Inches(1.45), my + Inches(0.33), right_col_w - Inches(1.6), Inches(0.28),
                     font_size=Pt(10), color=MUTED)

    # Distinction box
    box_y = Inches(6.75)
    add_card(slide, Inches(0.9), box_y, Inches(11.5), Inches(0.55), fill=CARD2,
             border=AMBER, border_width=Pt(1))
    add_text_box(slide,
                 "⚠  Local format check  ≠  Registry validation  ≠  Official identity verification   "
                 "·   QR verification confirms enrolment record integrity, not government identity.",
                 Inches(1.05), box_y + Inches(0.1), Inches(11.2), Inches(0.4),
                 font_size=Pt(11), color=AMBER)


def slide9_closing(prs):
    """Closing: VALIDATE. MONITOR. VERIFY."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = make_cover_bg()
    add_bg(slide, pil_img_to_stream(bg), W, H)
    add_rect(slide, 0, 0, Inches(0.06), H, CYAN)

    add_text_box(slide, "NEXT STEPS & CLOSING", Inches(0.9), Inches(0.25), Inches(8), Inches(0.4),
                 font_size=Pt(11), color=CYAN, bold=True)

    # 4-stage future roadmap
    stages = [
        (CYAN,  "Phase 1", "PILOT", "Deploy with 2–3 AICTE\ninstitutions on controlled\ndata set"),
        (AMBER, "Phase 2", "POLICY\nVALIDATION", "Align statutory rules with\nactual AICTE intake\nregulations"),
        (GREEN, "Phase 3", "INTEGRATION", "Official APAAR / DigiLocker\nconnection — subject to\nauthorisation"),
        (WHITE, "Phase 4", "NATIONAL\nROLLOUT", "Scale to all AICTE-approved\ninstitutions with production\ndatabase"),
    ]

    n = len(stages)
    box_w = Inches(2.7)
    box_h = Inches(1.9)
    gap = Inches(0.28)
    total_w = n * box_w + (n-1) * gap
    start_x = (W - total_w) / 2
    phase_y = Inches(1.1)

    for i, (color, phase, title, desc) in enumerate(stages):
        x = start_x + i * (box_w + gap)
        add_card(slide, x, phase_y, box_w, box_h, fill=CARD, border=color, border_width=Pt(1.5))
        add_text_box(slide, phase,
                     x + Inches(0.15), phase_y + Inches(0.1), box_w - Inches(0.25), Inches(0.3),
                     font_size=Pt(10), bold=True, color=color)
        add_text_box(slide, title,
                     x + Inches(0.15), phase_y + Inches(0.38), box_w - Inches(0.25), Inches(0.6),
                     font_size=Pt(14), bold=True, color=WHITE)
        add_text_box(slide, desc,
                     x + Inches(0.15), phase_y + Inches(0.98), box_w - Inches(0.25), Inches(0.9),
                     font_size=Pt(11), color=MUTED)
        if i < n - 1:
            ax = x + box_w + gap*0.1
            ay = phase_y + box_h/2
            ln = slide.shapes.add_connector(1, ax, ay, ax + gap*0.85, ay)
            ln.line.color.rgb = color
            ln.line.width = Pt(1.5)

    # Closing statement
    add_text_box(slide, "VALIDATE.", Inches(0.9), Inches(3.3), Inches(4.0), Inches(1.1),
                 font_size=Pt(44), bold=True, color=CYAN, align=PP_ALIGN.LEFT)
    add_text_box(slide, "MONITOR.", Inches(4.9), Inches(3.3), Inches(4.0), Inches(1.1),
                 font_size=Pt(44), bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    add_text_box(slide, "VERIFY.", Inches(8.9), Inches(3.3), Inches(3.6), Inches(1.1),
                 font_size=Pt(44), bold=True, color=GREEN, align=PP_ALIGN.RIGHT)

    # Sub-tagline
    add_text_box(slide,
                 "Building the trust infrastructure for India's higher education enrolment ecosystem.",
                 Inches(0.9), Inches(4.3), Inches(11.5), Inches(0.6),
                 font_size=Pt(17), color=MUTED, align=PP_ALIGN.CENTER)

    # Divider
    ln = slide.shapes.add_connector(1, Inches(0.9), Inches(5.1), Inches(12.4), Inches(5.1))
    ln.line.color.rgb = CYAN
    ln.line.width = Pt(1)

    # Team + repo info
    add_text_box(slide, "Team Sentinels", Inches(0.9), Inches(5.25), Inches(5), Inches(0.45),
                 font_size=Pt(16), bold=True, color=WHITE)
    add_text_box(slide,
                 "PS: SIH26263  ·  AICTE  ·  Software / Smart Automation",
                 Inches(0.9), Inches(5.65), Inches(8), Inches(0.4),
                 font_size=Pt(13), color=MUTED)

    # Working model QR thumbnail
    qr_path = os.path.join(ASSETS, "wm_06_qr_verify.png")
    if os.path.exists(qr_path):
        add_image(slide, qr_path, Inches(10.5), Inches(5.1), Inches(2.2), Inches(1.4))
        add_text_box(slide, "Live demo — QR verification", Inches(10.5), Inches(6.55), Inches(2.2), Inches(0.3),
                     font_size=Pt(9), color=MUTED, align=PP_ALIGN.CENTER)

    # Final reminder box
    add_card(slide, Inches(0.9), Inches(6.82), Inches(11.5), Inches(0.48), fill=CARD2)
    add_text_box(slide,
                 "All data shown is synthetic. SQLite is prototype-only. APAAR registry integration is planned, not active. "
                 "Validation engine uses 14 deterministic rules — not ML.",
                 Inches(1.05), Inches(6.88), Inches(11.2), Inches(0.4),
                 font_size=Pt(9.5), color=MUTED, italic=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H

    print("Building 9-slide SIH26263 presentation...")

    print("  [1/9] Cover")
    slide1_cover(prs)
    print("  [2/9] Problem")
    slide2_problem(prs)
    print("  [3/9] Solution")
    slide3_solution(prs)
    print("  [4/9] Differentiators")
    slide4_differentiators(prs)
    print("  [5/9] Architecture")
    slide5_architecture(prs)
    print("  [6/9] Validation Engine")
    slide6_validation(prs)
    print("  [7/9] Live Product")
    slide7_live_product(prs)
    print("  [8/9] Security & Impact")
    slide8_security(prs)
    print("  [9/9] Closing")
    slide9_closing(prs)

    out = r"c:\All_Projects\apaar-aicte-platform\SIH26263_v3_Final.pptx"
    prs.save(out)
    size_kb = os.path.getsize(out) // 1024
    print(f"\nSaved: {out}  ({size_kb} KB)")
    print("Open in Microsoft PowerPoint for best rendering.")

if __name__ == "__main__":
    main()
