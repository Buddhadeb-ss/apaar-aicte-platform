import os
from PIL import Image, ImageOps

ASSET_DIR = r"c:\All_Projects\apaar-aicte-platform\presentation_assets"

def process_images():
    # 1. Command Center: Top 750px of 1440x900 viewport
    cc_path = os.path.join(ASSET_DIR, "screen_command_center.png")
    if os.path.exists(cc_path):
        im = Image.open(cc_path)
        # Crop header + KPI cards + charts
        cropped = im.crop((0, 64, 1440, 820))
        cropped.save(os.path.join(ASSET_DIR, "hero_command_center.png"), quality=95)
        print("hero_command_center.png created:", cropped.size)

    # 2. Institution Portal: Course Capacity Allocation + Stats
    inst_path = os.path.join(ASSET_DIR, "screen_institution_portal.png")
    if os.path.exists(inst_path):
        im = Image.open(inst_path)
        cropped = im.crop((0, 64, 1440, 780))
        cropped.save(os.path.join(ASSET_DIR, "hero_institution_portal.png"), quality=95)
        print("hero_institution_portal.png created:", cropped.size)

    # 3. Student Credential Pass: Center card
    stud_path = os.path.join(ASSET_DIR, "screen_student_pass.png")
    if os.path.exists(stud_path):
        im = Image.open(stud_path)
        # Center card is between x: 200 to 1240, y: 80 to 760
        cropped = im.crop((180, 70, 1260, 780))
        cropped.save(os.path.join(ASSET_DIR, "hero_student_pass.png"), quality=95)
        print("hero_student_pass.png created:", cropped.size)

    # 4. Validation Workbench: Rules + Risk score table
    val_path = os.path.join(ASSET_DIR, "screen_validation_workbench.png")
    if os.path.exists(val_path):
        im = Image.open(val_path)
        cropped = im.crop((0, 64, 1440, 800))
        cropped.save(os.path.join(ASSET_DIR, "hero_validation_workbench.png"), quality=95)
        print("hero_validation_workbench.png created:", cropped.size)

if __name__ == "__main__":
    process_images()

