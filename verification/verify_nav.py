from playwright.sync_api import sync_playwright

def verify_dashboard_date_nav():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Login
        page.goto("http://localhost:8000/static/index.html")
        page.fill("#username", "johndoe")
        page.fill("#password", "securepass")
        page.click("button[type=submit]")
        page.wait_for_selector("#dashboard-view", state="visible")

        # 2. Check Date Title (Should be "Today's Summary")
        title = page.locator("#dashboard-date-title").inner_text()
        print(f"Initial Title: {title}")
        assert "Today's Summary" in title

        # 3. Click Prev
        page.click("text=< Prev")
        page.wait_for_timeout(500) # Wait for JS update

        # 4. Check Date Title (Should be "Daily Summary" and not Today)
        title_prev = page.locator("#dashboard-date-title").inner_text()
        date_display = page.locator("#current-date-display").inner_text()
        print(f"Prev Title: {title_prev}")
        print(f"Prev Date: {date_display}")
        assert "Daily Summary" in title_prev

        # 5. Screenshot Dashboard
        page.screenshot(path="verification/dashboard_nav.png")
        print("Screenshot dashboard_nav.png saved")

        # 6. Check Reports Tab for Breakdown
        page.click("button[onclick=\"showTab('reports')\"]")
        page.wait_for_selector("#med-breakdown-table", state="visible")
        page.screenshot(path="verification/reports_breakdown.png")
        print("Screenshot reports_breakdown.png saved")

        browser.close()

if __name__ == "__main__":
    verify_dashboard_date_nav()
