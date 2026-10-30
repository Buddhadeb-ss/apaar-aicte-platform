import os
from playwright.sync_api import sync_playwright

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUTPUT_DIR = r"c:\All_Projects\apaar-aicte-platform\presentation_assets"

def capture_modals():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=EDGE_PATH, headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("[1/2] Capturing Collision Modal...")
        page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        page.wait_for_timeout(2500)
        # Click collision alert badge / card
        collision_trigger = page.locator("button:has-text('Collision Discrepancy')").or_(page.locator("button:has-text('View Collision Alert')")).or_(page.locator("span:has-text('Collision Alert')")).first
        if collision_trigger.is_visible():
            collision_trigger.click()
            page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "screen_collision_modal.png"))

        print("[2/2] Capturing Verification Scan Result...")
        # Navigate to Verification portal
        page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        verify_btn = page.locator("nav button:has-text('Verify')").first
        if verify_btn.is_visible():
            verify_btn.click()
            page.wait_for_timeout(1000)
            # Click quick sample token or paste
            sample_btn = page.locator("button:has-text('Sample Token')").or_(page.locator("button:has-text('Paste Sample')")).or_(page.locator("button:has-text('Verify Digital Credential')")).first
            if sample_btn.is_visible():
                sample_btn.click()
                page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "screen_verification_result.png"))

        browser.close()
        print("Modals captured!")

if __name__ == "__main__":
    capture_modals()

