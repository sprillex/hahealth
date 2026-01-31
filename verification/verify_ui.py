from playwright.sync_api import sync_playwright, expect
import os
import time

def test_ui(page):
    # Set viewport to desktop
    page.set_viewport_size({"width": 1280, "height": 720})

    # 1. Go to Login
    page.goto("http://localhost:8000/")

    # 2. Login
    page.fill("#username", "testuser")
    page.fill("#password", "password")
    page.click("button[type=submit]")

    # Wait for Dashboard (Toast might appear)
    # The dashboard is #dashboard-view
    page.wait_for_selector("#dashboard-view", state="visible")

    # Wait a bit for potential animations
    time.sleep(1)

    # Screenshot 1: Dashboard with Icons
    page.screenshot(path="/home/jules/verification/1_dashboard.png")
    print("Screenshot 1: Dashboard taken")

    # 3. Navigate to Health Logs (Desktop Nav)
    # Find button with text 'Health Logs' inside .nav-links
    page.locator(".nav-links button:has-text('Health Logs')").click()

    # Wait for Action Cards
    page.wait_for_selector(".action-card")
    time.sleep(0.5)

    # Screenshot 2: Health Logs Tab (Action Cards)
    page.screenshot(path="/home/jules/verification/2_health_logs.png")
    print("Screenshot 2: Health Logs taken")

    # 4. Open BP Modal
    page.click("div.action-card:has-text('Log Blood Pressure')")
    page.wait_for_selector("#log-bp-modal", state="visible")
    time.sleep(0.5)

    # Screenshot 3: BP Modal
    page.screenshot(path="/home/jules/verification/3_bp_modal.png")
    print("Screenshot 3: BP Modal taken")

    # Close Modal
    page.click("#log-bp-modal .close")
    time.sleep(0.5)

    # 5. Navigate to Food (Nutrition)
    page.locator(".nav-links button:has-text('Food')").click()

    # Wait for Nav
    page.wait_for_selector(".nutrition-nav-container")
    time.sleep(0.5)

    # Screenshot 4: Nutrition Nav
    page.screenshot(path="/home/jules/verification/4_nutrition.png")
    print("Screenshot 4: Nutrition Nav taken")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            test_ui(page)
        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="/home/jules/verification/error.png")
        finally:
            browser.close()
