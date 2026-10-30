import os
import time
from playwright.sync_api import sync_playwright

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUTPUT_DIR = r"c:\All_Projects\apaar-aicte-platform\presentation_assets"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def capture_screens():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=EDGE_PATH, headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("[1/5] Capturing AICTE Command Center...")
        page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "screen_command_center.png"))

        print("[2/5] Capturing Validation Workbench...")
        workbench_btn = page.locator("button:has-text('Validation Workbench')").first
        if workbench_btn.is_visible():
            workbench_btn.click()
            page.wait_for_timeout(2000)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "screen_validation_workbench.png"))

        print("[3/5] Capturing Institutional Portal (Apex Tech)...")
        # Click on user menu dropdown and switch persona to Apex Tech
        dropdown_btn = page.locator("header button:has-text('Dr. K. S. Sundaram')").or_(page.locator("header button:has-text('AICTE')")).last
        if dropdown_btn.is_visible():
            dropdown_btn.click()
            page.wait_for_timeout(500)
            apex_btn = page.locator("button:has-text('Apex Institute Registrar')").or_(page.locator("button:has-text('registrar@apex.edu')")).first
            if apex_btn.is_visible():
                apex_btn.click()
                page.wait_for_timeout(2500)
                page.screenshot(path=os.path.join(OUTPUT_DIR, "screen_institution_portal.png"))

        print("[4/5] Capturing Student Credential Pass...")
        dropdown_btn = page.locator("header button").filter(has_text="Prof. Sunita").or_(page.locator("header button").filter(has_text="Registrar")).last
        if dropdown_btn.is_visible():
            dropdown_btn.click()
            page.wait_for_timeout(500)
            student_btn = page.locator("button:has-text('Aarav Sharma')").or_(page.locator("button:has-text('student@apex.edu')")).first
            if student_btn.is_visible():
                student_btn.click()
                page.wait_for_timeout(2500)
                page.screenshot(path=os.path.join(OUTPUT_DIR, "screen_student_pass.png"))

        print("[5/5] Capturing Verifier Portal...")
        verify_nav_btn = page.locator("button:has-text('Verify Credential')").or_(page.locator("button:has-text('verify-qr')")).first
        if not verify_nav_btn.is_visible():
            verify_nav_btn = page.locator("nav button:has-text('Verify')").first
        if verify_nav_btn.is_visible():
            verify_nav_btn.click()
            page.wait_for_timeout(2000)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "screen_verifier_portal.png"))

        browser.close()
        print("All screen assets successfully captured!")

if __name__ == "__main__":
    capture_screens()

