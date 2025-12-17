from playwright.sync_api import sync_playwright

def verify_bp_history():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to home
        page.goto("http://localhost:8000/static/index.html")

        # Login
        page.fill("#username", "johndoe")
        page.fill("#password", "securepass")
        page.click("button[type=submit]")

        # Wait for dashboard to load
        page.wait_for_selector("#dashboard-view", state="visible")

        # Click Reports tab
        page.click("button[onclick=\"showTab('reports')\"]")

        # Wait for tab content
        page.wait_for_selector("#tab-reports", state="visible")

        # Wait for table
        page.wait_for_selector("#bp-history-table", state="visible")

        # Wait for data to populate (look for 'Left Arm' text which we just logged)
        try:
            page.wait_for_selector("text=Left Arm", timeout=5000)
        except:
            print("Did not find 'Left Arm' in table, proceeding to screenshot anyway.")

        # Screenshot
        page.screenshot(path="verification/bp_history.png")
        print("Screenshot saved to verification/bp_history.png")

        browser.close()

if __name__ == "__main__":
    verify_bp_history()
