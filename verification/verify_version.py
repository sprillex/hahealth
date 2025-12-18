from playwright.sync_api import sync_playwright

def verify_version_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Login
        page.goto("http://localhost:8000/static/index.html")
        page.fill("#username", "johndoe")
        page.fill("#password", "securepass")
        page.click("button[type=submit]")
        page.wait_for_selector("#dashboard-view", state="visible")

        # 2. Check Footer
        page.wait_for_selector("footer", state="visible")
        footer_text = page.locator("footer").inner_text()
        print(f"Footer Text: {footer_text}")
        assert "v1.5.0" in footer_text

        # Screenshot
        page.screenshot(path="verification/version_footer.png")
        print("Screenshot saved to verification/version_footer.png")

        browser.close()

if __name__ == "__main__":
    verify_version_ui()
