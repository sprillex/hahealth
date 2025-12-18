from playwright.sync_api import sync_playwright

def verify_reports_enhancement():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Login
        page.goto("http://localhost:8000/static/index.html")
        page.fill("#username", "johndoe")
        page.fill("#password", "securepass")
        page.click("button[type=submit]")
        page.wait_for_selector("#dashboard-view", state="visible")

        # 2. Go to Reports
        page.click("button[onclick=\"showTab('reports')\"]")
        page.wait_for_selector("#tab-reports", state="visible")

        # 3. Check for User Info Section (Wait for ID that we will add)
        # Note: I haven't added the code yet, so this test will fail until I implement step 5.
        # But this is the verification plan.
        # page.wait_for_selector("#report-user-info", state="visible")

        # 4. Check for Medication Schedule Column
        # page.wait_for_selector("#med-breakdown-table th:has-text('Schedule')", state="visible")

        # 5. Check for Vaccinations Section
        # page.wait_for_selector("h3:has-text('Vaccinations')", state="visible")

        # 6. Check for Allergies Section
        # page.wait_for_selector("h3:has-text('Allergies')", state="visible")

        # Screenshot
        # page.screenshot(path="verification/reports_enhanced.png")

        browser.close()

if __name__ == "__main__":
    verify_reports_enhancement()
