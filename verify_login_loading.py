from playwright.sync_api import sync_playwright
import time

def verify_login_page():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Capture console logs
        page.on("console", lambda msg: print(f"Console: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"Page Error: {exc}"))

        try:
            response = page.goto("http://localhost:8000/")
            print(f"Page loaded: {response.status}")

            # Wait for version to load
            try:
                page.wait_for_selector("#app-version", timeout=5000)
                version_text = page.locator("#app-version").inner_text()
                print(f"Version text: {version_text}")

                if "Loading" in version_text:
                    print("FAIL: Version text still says Loading")
                else:
                    print("SUCCESS: Version loaded")
            except Exception as e:
                print(f"Wait failed: {e}")

        except Exception as e:
            print(f"Navigation failed: {e}")

        browser.close()

if __name__ == "__main__":
    verify_login_page()
