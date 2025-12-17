from playwright.sync_api import sync_playwright

def verify_bp_timezone():
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
        page.wait_for_selector("#bp-history-table", state="visible")

        # 3. Check Timestamp Format
        # We need to wait for rows.
        try:
             page.wait_for_selector("#bp-history-table tbody tr td", timeout=5000)
        except:
             print("No data in table?")

        # 4. Screenshot
        page.screenshot(path="verification/bp_timezone.png")
        print("Screenshot saved to verification/bp_timezone.png")

        browser.close()

if __name__ == "__main__":
    verify_bp_timezone()
