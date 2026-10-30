import os
from playwright.sync_api import sync_playwright

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUTPUT_DIR = r"c:\All_Projects\apaar-aicte-platform\presentation_assets"

def capture_extra_screens():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=EDGE_PATH, headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Login Page
        page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        page.wait_for_timeout(1000)
        # Log out if logged in
        logout_btn = page.locator("button:has-text('Logout')").or_(page.locator("button:has-text('Sign Out')")).first
        if logout_btn.is_visible():
            logout_btn.click()
            page.wait_for_timeout(1000)
        else:
            # Click user menu then logout
            user_btn = page.locator("header button").last
            if user_btn.is_visible():
                user_btn.click()
                page.wait_for_timeout(500)
                l_btn = page.locator("button:has-text('Sign Out')").or_(page.locator("button:has-text('Logout')")).first
                if l_btn.is_visible():
                    l_btn.click()
                    page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "screen_login.png"))
        print("screen_login.png captured!")

        # 2. Bulk Upload Wizard
        page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        page.wait_for_timeout(1500)
        # Login as apex admin
        apex_btn = page.locator("button:has-text('Apex Institute Registrar')").first
        if apex_btn.is_visible():
            apex_btn.click()
            page.wait_for_timeout(1500)
            wizard_tab = page.locator("button:has-text('Bulk Import Wizard')").or_(page.locator("button:has-text('Import')")).first
            if wizard_tab.is_visible():
                wizard_tab.click()
                page.wait_for_timeout(1500)
                page.screenshot(path=os.path.join(OUTPUT_DIR, "screen_wizard.png"))
                print("screen_wizard.png captured!")

        browser.close()

if __name__ == "__main__":
    capture_extra_screens()

