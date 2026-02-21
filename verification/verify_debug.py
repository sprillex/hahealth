import os
import time
from playwright.sync_api import sync_playwright

def verify_debug_mode():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Navigating to login...")
        page.goto("http://localhost:3000/")
        page.fill("#username", "admin")
        page.fill("#password", "password")
        page.click("button[type=submit]")

        print("Waiting for dashboard...")
        try:
            page.wait_for_selector("#dashboard-summary-card", state="visible", timeout=10000)
        except:
            print("Dashboard not found. Check login.")
            page.screenshot(path="verification/error_login.png")
            raise

        print("Navigating to Admin tab...")
        page.wait_for_selector("#nav-admin:not(.hidden)", state="visible", timeout=5000)
        page.click("#nav-admin")

        print("Toggling Debug Mode...")
        page.wait_for_selector("#debug-mode-toggle", state="visible")
        page.check("#debug-mode-toggle")

        # Verify Class on Body
        body_class = page.evaluate("document.body.className")
        print(f"Body class: {body_class}")
        if "debug-mode" not in body_class:
            print("Error: debug-mode class not added to body")
        else:
            print("Success: debug-mode class present.")

        # Screenshot Admin Panel
        page.screenshot(path="verification/debug_mode_admin.png")
        print("Screenshot saved: verification/debug_mode_admin.png")

        # Navigate back to Dashboard to see labels
        print("Navigating back to Dashboard...")
        # Desktop Nav
        page.click(".nav-links button:has-text('Dashboard')")

        page.wait_for_selector("#dashboard-summary-card")

        # Screenshot Dashboard
        page.screenshot(path="verification/debug_mode_dashboard.png")
        print("Screenshot saved: verification/debug_mode_dashboard.png")

        browser.close()

if __name__ == "__main__":
    verify_debug_mode()
