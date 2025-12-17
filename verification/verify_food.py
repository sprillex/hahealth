from playwright.sync_api import sync_playwright

def verify_food_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Login
        page.goto("http://localhost:8000/static/index.html")
        page.fill("#username", "johndoe")
        page.fill("#password", "securepass")
        page.click("button[type=submit]")
        page.wait_for_selector("#dashboard-view", state="visible")

        # 2. Click Nutrition Tab
        page.click("button[onclick=\"showTab('nutrition')\"]")
        page.wait_for_selector("#tab-nutrition", state="visible")

        # 3. Create Custom Food
        page.click("button[onclick=\"openFoodModal()\"]")
        page.wait_for_selector("#food-modal", state="visible")

        # Use explicit selectors with parent ID to avoid ambiguity with Log Exercise form
        page.fill("#create-food-form input[name='food_name']", "Custom Apple")
        page.fill("#create-food-form input[name='calories']", "95")

        # Submit
        page.click("#create-food-form button[type='submit']")

        # Wait for alert or modal close
        page.on("dialog", lambda dialog: dialog.accept())
        page.wait_for_selector("#food-modal", state="hidden")

        # 4. Search for it
        page.fill("#food-search-input", "Custom Apple")
        # Wait for results
        page.wait_for_selector(".search-item", state="visible", timeout=10000)

        # 5. Select and Log
        page.click(".search-item:has-text('Custom Apple')")
        page.click("#food-log-form button[type='submit']")

        # Screenshot
        page.screenshot(path="verification/food_ui.png")
        print("Screenshot saved to verification/food_ui.png")

        browser.close()

if __name__ == "__main__":
    verify_food_ui()
