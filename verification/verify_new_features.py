from playwright.sync_api import sync_playwright

def verify_dob_and_edit():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Login
        page.goto("http://localhost:8000/static/index.html")
        page.fill("#username", "johndoe")
        page.fill("#password", "securepass")
        page.click("button[type=submit]")
        page.wait_for_selector("#dashboard-view", state="visible")

        # 2. Settings - Update DOB
        page.click("button[onclick=\"showTab('settings')\"]")
        page.wait_for_selector("#tab-settings", state="visible")
        page.fill("#profile-dob", "1990-01-01")
        page.click("#profile-form button[type='submit']")
        page.on("dialog", lambda dialog: dialog.accept())

        # 3. Reports - Verify DOB
        page.click("button[onclick=\"showTab('reports')\"]")
        page.wait_for_selector("#tab-reports", state="visible")
        page.wait_for_timeout(500)

        dob_text = page.locator("#rep-dob").inner_text()
        print(f"DOB on Report: {dob_text}")
        assert "1990" in dob_text or "January" in dob_text

        # 4. Settings - Allergies
        page.click("button[onclick=\"showTab('settings')\"]")
        # Use specific selector for Allergy Add button
        page.click("button[onclick='openAllergyModal()']")
        page.wait_for_selector("#allergy-modal", state="visible")
        page.fill("input[name='allergen']", "TestAllergy")
        page.click("#allergy-form button[type='submit']")
        page.wait_for_selector("#allergy-modal", state="hidden")

        # 5. Edit Allergy
        # Find 'Edit' button next to TestAllergy
        page.wait_for_selector("li:has-text('TestAllergy')", state="visible")
        page.click("li:has-text('TestAllergy') button:has-text('Edit')")
        page.wait_for_selector("#allergy-modal", state="visible")

        # Change name
        page.fill("input[name='allergen']", "UpdatedAllergy")
        page.click("#allergy-form button[type='submit']")
        page.wait_for_selector("#allergy-modal", state="hidden")

        # Verify update
        page.wait_for_selector("li:has-text('UpdatedAllergy')", state="visible")
        print("Allergy Update Verified")

        # 6. Screenshot
        page.screenshot(path="verification/dob_edit.png")
        print("Screenshot saved to verification/dob_edit.png")

        browser.close()

if __name__ == "__main__":
    verify_dob_and_edit()
