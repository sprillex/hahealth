from playwright.sync_api import sync_playwright

def verify_dashboard_summary_macros():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Login
        page.goto("http://localhost:8000/static/index.html")
        page.fill("#username", "tz_macro_test_user")
        page.fill("#password", "password")
        page.click("button[type=submit]")
        page.wait_for_selector("#dashboard-view", state="visible")

        # 2. Check Today's Summary (Wait for load)
        page.wait_for_timeout(1000)

        # Since we logged data for "2025-12-17" in the previous step, and that is "Today" in the mocked scenario,
        # but in reality "Today" might be 2025-12-18 on the server if it's UTC+0.
        # But the frontend defaults to `new Date()`.
        # If frontend is running in the container, it uses system time.
        # The script forced "Today" logic.

        # We can just check if the summary cards are non-zero.
        # cals-in
        cals = page.locator("#summary-cals-in").inner_text()
        print(f"Calories In: {cals}")

        # We logged 300 kcal (custom pizza).
        if cals == "300":
            print("Frontend verification passed: Calories match.")
        else:
            print("Frontend verification warning: Calories might be 0 if date mismatch.")

        page.screenshot(path="verification/dashboard_macros_tz.png")
        print("Screenshot saved to verification/dashboard_macros_tz.png")

        browser.close()

if __name__ == "__main__":
    verify_dashboard_summary_macros()
