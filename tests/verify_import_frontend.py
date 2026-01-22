from playwright.sync_api import sync_playwright, expect
import json
import os
import time

def verify_import_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Login
        print("Logging in...")
        page.goto("http://localhost:8000")
        page.fill("#username", "admin")
        page.fill("#password", "admin")
        page.click("button[type=submit]")

        expect(page.locator("#dashboard-view")).to_be_visible()
        print("Logged in.")

        # 2. Go to Nutrition
        page.click("button[onclick=\"showTab('nutrition')\"]")
        expect(page.locator("#tab-nutrition")).to_be_visible()

        # 3. Open Import Modal
        import_btn = page.locator("#btn-import-json")
        expect(import_btn).to_be_visible()
        import_btn.click()
        expect(page.locator("#import-json-modal")).to_be_visible()

        # 4. Prepare JSON Payload (New Food)
        new_food_json = json.dumps({
            "quantity": 1.0,
            "variables": {
                "NewFrontendFood": {
                    "metadata": {"name": "New Frontend Food", "upc": "888888001"},
                    "macros": {"calories": 100, "protein_g": 10, "fat_g": 5, "carbs_g": 10}
                }
            }
        })

        # 5. Fill and Preview
        page.fill("#import-json-text", new_food_json)
        page.click("button:has-text('Preview')")
        expect(page.locator("#btn-import-submit")).to_be_visible()

        # 6. Import (Should verify success alert)
        print("Importing new food...")

        # Reset dialog handler
        dialogs_1 = []
        def handle_dialog_1(dialog):
             print(f"Dialog 1: {dialog.message}")
             dialogs_1.append(dialog.message)
             dialog.accept()
        page.on("dialog", handle_dialog_1)

        page.click("#btn-import-submit")

        # Wait for alert
        page.wait_for_timeout(1000)

        assert any("Successfully" in msg for msg in dialogs_1), f"First import failed: {dialogs_1}"
        page.remove_listener("dialog", handle_dialog_1)


        # 7. Import Existing Food (Should trigger Conflict confirmation)
        print("Importing existing food (should trigger conflict)...")
        # Re-open modal
        import_btn.click()
        page.fill("#import-json-text", new_food_json)
        page.click("button:has-text('Preview')")

        dialogs_2 = []
        def handle_dialog_2(dialog):
            print(f"Dialog 2: {dialog.message}")
            dialogs_2.append(dialog.message)
            dialog.accept()

        page.on("dialog", handle_dialog_2)

        page.click("#btn-import-submit")

        # Wait for operations to complete
        page.wait_for_timeout(2000)

        # Verify we got two dialogs:
        # 1. "Food already exists..." (Confirmation)
        # 2. "Food Imported / Updated Successfully!" (Alert)

        print(f"Captured dialogs round 2: {dialogs_2}")

        assert any("already exists" in msg for msg in dialogs_2), "Did not see conflict confirmation"
        assert any("Successfully" in msg for msg in dialogs_2), "Did not see success message"

        # Screenshot
        page.screenshot(path="verification_import.png")
        print("Verification complete. Screenshot saved.")

        browser.close()

if __name__ == "__main__":
    verify_import_frontend()
