import os
import time
from playwright.sync_api import sync_playwright, expect

def verify_popup_log():
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

        print("Clicking [+ Log]...")
        page.get_by_text("[+ Log]").click()

        print("Searching 'Apple'...")
        page.fill("#modal-food-search-input", "Apple")
        page.wait_for_selector("#modal-food-search-results .search-item", state="visible", timeout=5000)

        print("Selecting result...")
        page.click("#modal-food-search-results .search-item:first-child")

        print("Submitting initial form (triggers Preview)...")
        page.click("#modal-food-log-form button[type=submit]")

        print("Waiting for Preview Modal...")
        page.wait_for_selector("#food-preview-modal", state="visible", timeout=5000)

        print("Clicking Confirm Log in Preview...")
        # There might be two 'Confirm Log' buttons (one sticky mobile, one normal).
        # Click the visible one or first one.
        page.click("#food-preview-modal button.btn-primary:visible")

        print("Waiting for success toast...")
        page.wait_for_selector(".toast.success", state="visible", timeout=5000)
        print("Success toast confirmed!")

        page.screenshot(path="verification/popup_log_success.png")
        print("Screenshot saved.")

        browser.close()

if __name__ == "__main__":
    try:
        verify_popup_log()
    except Exception as e:
        print(f"Verification Failed: {e}")
        exit(1)
