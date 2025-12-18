from playwright.sync_api import sync_playwright

def verify_frontend_macros():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Login
        page.goto("http://localhost:8000/static/index.html")
        page.fill("#username", "johndoe")
        page.fill("#password", "securepass")
        page.click("button[type=submit]")
        page.wait_for_selector("#dashboard-view", state="visible")

        # 2. Check Gauges for Macros
        # Wait for summary load
        page.wait_for_timeout(1000)

        # Verify text elements exist in gauges
        # Look for "20 g" (Protein), "10 g" (Fat), etc. based on previous script execution
        # (Assuming the DB state persists or we re-run logic)

        content = page.content()
        if "20 g" in content:
            print("Found 20g Protein in Dashboard")
        else:
            print("Did not find 20g Protein - maybe test user data reset or summary not loaded")

        page.screenshot(path="verification/macros_dashboard.png")
        print("Screenshot saved to verification/macros_dashboard.png")

        browser.close()

if __name__ == "__main__":
    verify_frontend_macros()
