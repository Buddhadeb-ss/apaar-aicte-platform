import os
from PIL import Image, ImageDraw, ImageFont

ASSET_DIR = r"c:\All_Projects\apaar-aicte-platform\presentation_assets"

def create_sih_logo():
    # SIH emblem: 300x120 transparent PNG
    im = Image.new("RGBA", (340, 110), (255, 255, 255, 0))
    draw = ImageDraw.Draw(im)

    try:
        font_sih = ImageFont.truetype("arialbd.ttf", 22)
        font_sub = ImageFont.truetype("arialbd.ttf", 16)
        font_tiny = ImageFont.truetype("arial.ttf", 12)
    except:
        font_sih = font_sub = font_tiny = ImageFont.load_default()

    # Draw gear/lightbulb icon on the left
    # Draw gear teeth circle
    draw.ellipse([(15, 15), (75, 75)], fill=(249, 115, 22, 255)) # Orange
    draw.ellipse([(35, 15), (75, 75)], fill=(16, 185, 129, 255)) # Green half
    draw.ellipse([(27, 27), (63, 63)], fill=(255, 255, 255, 255)) # White center
    draw.text((32, 35), "SIH", font=font_tiny, fill=(30, 41, 59, 255))

    # Text
    draw.text((95, 18), "SMART INDIA", font=font_sih, fill=(30, 41, 59, 255))
    draw.text((95, 44), "HACKATHON", font=font_sih, fill=(30, 41, 59, 255))
    draw.text((95, 72), "2026", font=font_sub, fill=(249, 115, 22, 255))

    im.save(os.path.join(ASSET_DIR, "sih_logo_badge.png"))
    print("sih_logo_badge.png created!")

def create_tech_stack_grid():
    # 8 rounded icon cards in 2 rows of 4
    w, h = 500, 240
    im = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    draw = ImageDraw.Draw(im)

    try:
        font_name = ImageFont.truetype("arialbd.ttf", 15)
        font_sub = ImageFont.truetype("arial.ttf", 11)
    except:
        font_name = font_sub = ImageFont.load_default()

    icons = [
        ("FastAPI", "REST Core", (13, 148, 136)),       # Teal
        ("React 18", "TypeScript", (2, 132, 199)),     # Sky Blue
        ("Python 3.13", "Engine", (59, 130, 246)),     # Blue
        ("SQLAlchemy", "ORM DB", (217, 119, 6)),       # Amber
        ("Tailwind CSS", "UI Design", (14, 165, 233)),  # Cyan
        ("Recharts", "Analytics", (244, 63, 94)),      # Rose
        ("HMAC-256", "QR Crypto", (124, 58, 237)),     # Purple
        ("Verhoeff", "Checksum", (16, 185, 129))       # Emerald
    ]

    for i, (name, role, color) in enumerate(icons):
        row = i // 4
        col = i % 4
        x = col * 122 + 6
        y = row * 116 + 6

        # Draw rounded card with subtle drop shadow
        draw.rounded_rectangle([(x, y), (x + 112, y + 104)], radius=14, fill=(248, 250, 252, 255), outline=(226, 232, 240, 255), width=2)
        # Color badge on top
        draw.rounded_rectangle([(x + 36, y + 14), (x + 76, y + 46)], radius=8, fill=color)
        draw.text((x + 42, y + 18), name[:2].upper(), font=font_name, fill=(255, 255, 255, 255))
        # Text
        draw.text((x + 12, y + 56), name, font=font_name, fill=(15, 23, 42, 255))
        draw.text((x + 12, y + 78), role, font=font_sub, fill=(100, 116, 139, 255))

    im.save(os.path.join(ASSET_DIR, "tech_stack_grid.png"))
    print("tech_stack_grid.png created!")

def crop_working_model_screens():
    # Create 6 uniform thumbnails for Slide 4 (Working Model): 640x380
    screens = [
        ("screen_login.png", "wm_01_login.png", (0, 0, 1440, 900)),
        ("screen_institution_portal.png", "wm_02_college_portal.png", (0, 60, 1440, 860)),
        ("hero_command_center.png", "wm_03_command_center.png", (0, 0, 1440, 756)),
        ("hero_collision_graphic.png", "wm_04_collision.png", (0, 0, 1200, 700)),
        ("hero_validation_workbench.png", "wm_05_workbench.png", (0, 0, 1440, 736)),
        ("hero_student_pass.png", "wm_06_qr_verify.png", (0, 0, 1080, 710))
    ]

    target_size = (680, 420)
    for src_name, out_name, box in screens:
        src_path = os.path.join(ASSET_DIR, src_name)
        if os.path.exists(src_path):
            im = Image.open(src_path)
            cropped = im.crop(box)
            resized = cropped.resize(target_size, Image.Resampling.LANCZOS)
            # Add a clean 2px light-gray border around thumbnail
            bordered = Image.new("RGB", (target_size[0] + 4, target_size[1] + 4), (203, 213, 225))
            bordered.paste(resized, (2, 2))
            bordered.save(os.path.join(ASSET_DIR, out_name), quality=95)
            print(f"{out_name} saved!")

if __name__ == "__main__":
    create_sih_logo()
    create_tech_stack_grid()
    crop_working_model_screens()

