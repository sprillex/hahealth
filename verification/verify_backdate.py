import os
import time
import datetime
from playwright.sync_api import sync_playwright, expect

def verify_backdate():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))

        print("Logging in...")
        page.goto("http://localhost:3000/")
        page.fill("#username", "admin")
        page.fill("#password", "password")
        page.click("button[type=submit]")

        print("Waiting for dashboard...")
        page.wait_for_selector("#dashboard-summary-card", state="visible")

        print("Navigating to Yesterday...")
        # Click 'Prev' button
        page.click(".date-nav button:first-child")
        time.sleep(1) # wait for refresh

        print("Opening [+ Log] modal...")
        page.get_by_text("[+ Log]").click()
        page.wait_for_selector("#log-food-modal", state="visible")

        print("Logging item...")
        page.fill("#modal-food-search-input", "Apple")
        page.wait_for_selector("#modal-food-search-results .search-item", state="visible", timeout=5000)
        page.click("#modal-food-search-results .search-item:first-child")

        # NOTE: Clicking search item triggers openPreviewModal immediately if names match.
        # But for 'Apple', it might not match exactly if search result is 'Apple (95 kcal)'.
        # App logic: if selectedFoodItem && selectedFoodItem.food_name === data.food_name then open preview.
        # When clicking search item, it sets input to food_name. So it should match.

        # Submitting via button.
        # If preview modal logic is triggered, this click might be redundant or intercepted?
        # Actually, clicking result populates input. Then we must click 'Log Food'.
        page.click("#modal-food-log-form button[type=submit]")

        # Confirm preview if it appears (it should)
        try:
            page.wait_for_selector("#food-preview-modal", state="visible", timeout=3000)
            print("Preview modal appeared. Confirming...")
            page.click("#food-preview-modal button.btn-primary:visible")
        except:
            print("No preview modal or timeout.")

        print("Waiting for success toast...")
        page.wait_for_selector(".toast.success", state="visible")

        # Verify the log appeared on the CURRENT view (Yesterday)
        time.sleep(1)
        content = page.text_content("#food-today-list")
        print(f"List content: {content}")

        if "Apple" in content or "apple" in content.lower():
            print("SUCCESS: Item found on Yesterday's list.")
        else:
            print(f"FAILURE: Item NOT found on Yesterday's list.")
            raise Exception("Backdating failed or list not updated.")

        page.screenshot(path="verification/backdate_success.png")
        browser.close()

if __name__ == "__main__":
    try:
        verify_backdate()
    except Exception as e:
        print(f"Verification Failed: {e}")
        exit(1)
