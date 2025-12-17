from playwright.sync_api import sync_playwright

def verify_frontend_timezone_setting():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Login
        page.goto("http://localhost:8000/static/index.html")
        page.fill("#username", "johndoe")
        page.fill("#password", "securepass")
        page.click("button[type=submit]")
        page.wait_for_selector("#dashboard-view", state="visible")

        # 2. Go to Settings
        page.click("button[onclick=\"showTab('settings')\"]")
        page.wait_for_selector("#tab-settings", state="visible")

        # 3. Check Timezone Dropdown exists
        page.wait_for_selector("#profile-timezone", state="visible")

        # 4. Check if it populated (should have options)
        options = page.locator("#profile-timezone option").count()
        print(f"Timezone options count: {options}")
        assert options > 1

        # 5. Screenshot
        page.screenshot(path="verification/timezone_ui.png")
        print("Screenshot saved to verification/timezone_ui.png")

        browser.close()

if __name__ == "__main__":
    verify_frontend_timezone_setting()
