from playwright.sync_api import sync_playwright, expect
import json
import os
import time

def verify_summary_display():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Login
        print("Logging in...")
        page.goto("http://localhost:8000")
        page.fill("#username", "admin")
        page.fill("#password", "admin")
        page.click("button[type=submit]")
        expect(page.locator("#dashboard-view")).to_be_visible()

        # 2. Create a food
        print("Creating food...")
        page.click("button[onclick=\"showTab('nutrition')\"]")
        page.click("button[onclick=\"openFoodModal()\"]")
        page.fill("#create-food-form [name='food_name']", "Test Summary Unit Food")
        page.fill("#create-food-form [name='calories']", "100")
        page.click("button:has-text('Create Food')")

        page.on("dialog", lambda d: d.accept())

        # 3. Log the food
        print("Logging food...")
        page.fill("#food-search-input", "Test Summary Unit Food")
        page.wait_for_selector(".search-item:has-text('Test Summary Unit Food')")
        page.click(".search-item:has-text('Test Summary Unit Food')")

        # Now click Log Food to trigger modal
        print("Clicking Log Food button...")
        page.click("#food-log-form button[type='submit']")

        # Wait for modal to appear (remove .hidden)
        print("Waiting for modal...")
        page.wait_for_selector("#food-preview-modal:not(.hidden)")

        print("Modal visible. Filling info...")
        page.fill("#preview-serving-size", "1.5")
        page.fill("#preview-quantity", "2")

        print("Confirming...")
        page.click("#food-preview-modal button:has-text('Confirm Log')")

        # Wait for modal to close (add .hidden)
        print("Waiting for modal to close...")
        expect(page.locator("#food-preview-modal")).to_be_hidden()

        # 4. Check Summary
        print("Checking summary...")
        page.click("button[onclick=\"showTab('dashboard')\"]")

        time.sleep(2)

        # Use .first to avoid strict mode error if duplicate logs exist
        list_item = page.locator("#food-today-list li:has-text('Test Summary Unit Food')").first
        expect(list_item).to_be_visible()

        text = list_item.inner_text()
        print(f"List Item Text: {text}")

        assert "2 x 1.5" in text, f"Quantity/Serving mismatch: {text}"

        print("Verification passed.")
        page.screenshot(path="verification_summary.png")
        browser.close()

if __name__ == "__main__":
    verify_summary_display()
