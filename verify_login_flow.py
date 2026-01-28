from playwright.sync_api import sync_playwright
import time

def verify_login_flow():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Capture console logs
        page.on("console", lambda msg: print(f"Console: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"Page Error: {exc}"))

        try:
            page.goto("http://localhost:8000/")

            # Fill Login
            page.fill("#username", "frontend_user")
            page.fill("#password", "password123")
            page.click("button[type=submit]")

            # Wait for dashboard
            try:
                page.wait_for_selector("#dashboard-view", state="visible", timeout=5000)
                print("SUCCESS: Dashboard visible")

                # Check for infinite loading texts
                # e.g. check if summary-bp is loaded
                page.wait_for_function("document.getElementById('summary-bp').innerText !== '--/--'", timeout=5000)
                print("SUCCESS: Summary loaded")

            except Exception as e:
                print(f"Dashboard wait failed: {e}")
                # Check if we are back at login?
                if page.is_visible("#auth-view"):
                    print("FAIL: Back at Auth View (Login failed/looped)")

        except Exception as e:
            print(f"Test failed: {e}")

        browser.close()

if __name__ == "__main__":
    verify_login_flow()
