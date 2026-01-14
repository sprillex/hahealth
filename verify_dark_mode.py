import time
from playwright.sync_api import sync_playwright, expect

def verify_dark_mode_search():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 1. Login
        page.goto("http://localhost:8000/")
        page.get_by_placeholder("Username").fill("testuser_nutri")
        page.get_by_placeholder("Password").fill("pw")
        page.get_by_role("button", name="Login").click()

        # Wait for dashboard
        expect(page.get_by_text("Today's Summary")).to_be_visible(timeout=5000)

        # 2. Go to Settings and Switch to Dark Mode
        page.get_by_role("button", name="Settings").click()
        page.locator("#theme-select").select_option("DARK")
        # Need to trigger change event? The select_option usually does.
        # But app.js logic: onchange="updateThemePreference(this.value)"

        # 3. Go to Nutrition Tab
        page.get_by_role("button", name="Nutrition").click()

        # 4. Search for "Playwright" (created in previous test, should exist)
        # Or create it if needed. Previous verification script created "Playwright Apple".
        # It's in the DB file if we are using the same running instance (which uses health_app.db).
        # We need to make sure the app created it.
        # The previous verification script ran against localhost:8000 which writes to health_app.db.
        # So it should be there.

        page.locator("#food-search-input").fill("Playwright")

        # Wait for results
        results = page.locator("#food-search-results")
        expect(results).to_be_visible()
        expect(results).to_contain_text("Playwright Apple")

        # Take screenshot to verify text visibility against dark background
        page.screenshot(path="/home/jules/verification/dark_mode_search.png")
        print("Screenshot taken")

        browser.close()

if __name__ == "__main__":
    verify_dark_mode_search()
