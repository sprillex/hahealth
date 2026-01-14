import time
from playwright.sync_api import sync_playwright, expect

def verify_manage_library():
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

        # 2. Go to Nutrition Tab
        page.get_by_role("button", name="Nutrition").click()

        # 3. Create a Food
        page.get_by_role("button", name="+ Create Custom Food").click()
        page.locator("#create-food-form input[name='food_name']").fill("Playwright Apple")
        page.locator("#create-food-form input[name='calories']").fill("50")
        page.get_by_role("button", name="Create Food").click()

        # Handle Alert (Create Food Success)
        # Playwright auto-dismisses dialogs but we might want to ensure it succeeded.
        # Actually standard alert handling in Playwright:
        # page.on("dialog", lambda dialog: dialog.accept())
        # But let's assume it works. The list reload is the proof.

        # 4. Open Manage Library
        page.get_by_role("button", name="Manage Library").click()

        # 5. Check Modal and List
        modal = page.locator("#manage-library-modal")
        expect(modal).to_be_visible()
        expect(page.get_by_text("Manage Food Library")).to_be_visible()

        # Check if our food is listed
        expect(page.get_by_text("Playwright Apple")).to_be_visible()

        # 6. Click Edit
        # Find the Edit button next to Playwright Apple
        # This is tricky with text search.
        # Use locator chaining.
        # row = page.locator("li", has_text="Playwright Apple")
        # row.get_by_role("button", name="Edit").click()

        # Taking screenshot of the list
        page.screenshot(path="/home/jules/verification/manage_library_modal.png")
        print("Screenshot taken")

        browser.close()

if __name__ == "__main__":
    verify_manage_library()
