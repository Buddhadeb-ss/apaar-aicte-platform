import os
from PIL import Image, ImageDraw, ImageFont

ASSET_DIR = r"c:\All_Projects\apaar-aicte-platform\presentation_assets"

def create_collision_graphic():
    # Width 1200, Height 700
    w, h = 1200, 700
    im = Image.new("RGBA", (w, h), (15, 23, 42, 255)) # Dark Slate Navy #0F172A
    draw = ImageDraw.Draw(im)

    try:
        font_large = ImageFont.truetype("arialbd.ttf", 36)
        font_title = ImageFont.truetype("arialbd.ttf", 26)
        font_body = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 16)
        font_mono = ImageFont.truetype("courbd.ttf", 20)
    except:
        font_large = font_title = font_body = font_small = font_mono = ImageFont.load_default()

    # Outer border
    draw.rounded_rectangle([(10, 10), (w-10, h-10)], radius=20, outline=(56, 189, 248, 120), width=2)

    # Top Student Identity Card
    draw.rounded_rectangle([(320, 40), (880, 190)], radius=16, fill=(30, 41, 59, 255), outline=(56, 189, 248, 255), width=2)
    draw.text((350, 60), "SINGLE PHYSICAL STUDENT IDENTITY", font=font_small, fill=(56, 189, 248, 255))
    draw.text((350, 85), "Vikram Malhotra", font=font_large, fill=(255, 255, 255, 255))
    draw.text((350, 135), "APAAR: •••• •••• •••• 5521  |  UUID: stud-vikram-2024", font=font_mono, fill=(203, 213, 225, 255))

    # Center Collision Alert Badge
    draw.rounded_rectangle([(410, 240), (790, 310)], radius=12, fill=(127, 29, 29, 255), outline=(239, 68, 68, 255), width=2)
    draw.text((435, 260), "⚠️  CENTRAL COLLISION DETECTED", font=font_title, fill=(254, 202, 202, 255))

    # Connecting Lines
    draw.line([(600, 190), (600, 240)], fill=(239, 68, 68, 255), width=4)
    draw.line([(600, 310), (600, 360)], fill=(239, 68, 68, 255), width=4)
    draw.line([(280, 360), (920, 360)], fill=(239, 68, 68, 255), width=4)
    draw.line([(280, 360), (280, 410)], fill=(239, 68, 68, 255), width=4)
    draw.line([(920, 360), (920, 410)], fill=(239, 68, 68, 255), width=4)

    # College 1 Card: Apex Tech
    draw.rounded_rectangle([(60, 410), (500, 640)], radius=16, fill=(30, 41, 59, 255), outline=(249, 115, 22, 255), width=2)
    draw.text((90, 435), "CONCURRENT ADMISSION #1", font=font_small, fill=(249, 115, 22, 255))
    draw.text((90, 465), "Apex Institute of Tech", font=font_title, fill=(255, 255, 255, 255))
    draw.text((90, 505), "Course: B.Tech Computer Science", font=font_body, fill=(226, 232, 240, 255))
    draw.text((90, 535), "Seat Roll: AIT-2024-CSE-099", font=font_mono, fill=(148, 163, 184, 255))
    draw.text((90, 565), "Academic Year: 2024-2025", font=font_small, fill=(148, 163, 184, 255))
    draw.text((90, 595), "Status: ACTIVE ENROLMENT (SEAT HELD)", font=font_small, fill=(239, 68, 68, 255))

    # College 2 Card: Beacon College
    draw.rounded_rectangle([(700, 410), (1140, 640)], radius=16, fill=(30, 41, 59, 255), outline=(56, 189, 248, 255), width=2)
    draw.text((730, 435), "CONCURRENT ADMISSION #2", font=font_small, fill=(56, 189, 248, 255))
    draw.text((730, 465), "Beacon College of Eng.", font=font_title, fill=(255, 255, 255, 255))
    draw.text((730, 505), "Course: B.Tech Info Technology", font=font_body, fill=(226, 232, 240, 255))
    draw.text((730, 535), "Seat Roll: BCE-2024-IT-045", font=font_mono, fill=(148, 163, 184, 255))
    draw.text((730, 565), "Academic Year: 2024-2025", font=font_small, fill=(148, 163, 184, 255))
    draw.text((730, 595), "Status: ACTIVE ENROLMENT (SEAT HELD)", font=font_small, fill=(239, 68, 68, 255))

    out_path = os.path.join(ASSET_DIR, "hero_collision_graphic.png")
    im.save(out_path)
    print("hero_collision_graphic.png created successfully!")

if __name__ == "__main__":
    create_collision_graphic()

