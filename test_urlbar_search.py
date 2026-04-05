"""
Test URL bar keyword search by simulating actual user typing in the address bar.
"""
from foxyz.sync_api import Foxyz
import time
import subprocess
import os

def test_urlbar_search():
    print("=== Testing URL bar keyword search ===")

    with Foxyz(headless=False) as browser:
        page = browser.new_page()

        # Navigate to about:blank first
        page.goto("about:blank")

        print("Waiting 20 seconds for Firefox search service to initialize...")
        time.sleep(20)

        # Check if search.json.mozlz4 was created
        import tempfile, glob
        profile_dirs = glob.glob("/tmp/playwright_firefoxdev_profile-*")
        if profile_dirs:
            profile = profile_dirs[-1]
            search_json = os.path.join(profile, "search.json.mozlz4")
            if os.path.exists(search_json):
                print(f"✅ search.json.mozlz4 EXISTS at {search_json} - search engines loaded!")
            else:
                print(f"❌ search.json.mozlz4 NOT FOUND in {profile}")
                # List profile files
                files = os.listdir(profile)
                print(f"  Profile files: {files[:20]}")

        print("\nAttempting URL bar search for 'foxyzuniquetestquery98765'...")

        # Focus URL bar with Cmd+L (Mac)
        page.keyboard.press("Meta+l")
        time.sleep(0.5)

        # Clear and type search query
        page.keyboard.press("Meta+a")
        page.keyboard.type("foxyzuniquetestquery98765")
        time.sleep(0.5)

        # Press Enter to navigate
        page.keyboard.press("Enter")

        # Wait for navigation
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception as e:
            print(f"  Wait error: {e}")

        time.sleep(3)
        url = page.url
        print(f"Result URL: {url}")

        if "google.com/search" in url:
            print("✅ SUCCESS: URL bar keyword search works! Google search triggered.")
        elif "foxyzuniquetestquery98765" in url:
            print("✅ SUCCESS: Search engine redirect happened (non-Google)")
        elif "about:neterror" in url or "neterror" in url:
            print("❌ FAILED: Got error page - treated as hostname")
        elif "about:blank" in url:
            print("❌ FAILED: Still on about:blank - URL bar didn't navigate")
        else:
            print(f"? Unknown result: {url}")

        # Test 2: multi-word search
        print("\nTest 2: multi-word search 'foxyz weather today'...")
        page.keyboard.press("Meta+l")
        time.sleep(0.5)
        page.keyboard.press("Meta+a")
        page.keyboard.type("foxyz weather today")
        time.sleep(0.5)
        page.keyboard.press("Enter")

        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception as e:
            print(f"  Wait error: {e}")

        time.sleep(3)
        url2 = page.url
        print(f"Result URL: {url2}")

        if "google.com/search" in url2:
            print("✅ SUCCESS: Multi-word search works!")
        elif "neterror" in url2:
            print("❌ FAILED: Got error page")
        else:
            print(f"? Result: {url2}")

        print("\n=== Press Ctrl+C to close ===")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    test_urlbar_search()
