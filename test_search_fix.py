"""
Test keyword search fix.
1. Check if search.json.mozlz4 is created (proves search engines loaded from Remote Settings)
2. Try page.goto("foxyzuniquesearchword") - Firefox URL fixup should redirect to Google if keyword.enabled=true
"""
from foxyz.sync_api import Foxyz
import time
import os
import glob

def get_profile_dir():
    """Find the playwright firefox profile directory."""
    patterns = [
        "/tmp/playwright_firefoxdev_profile-*",
        "/private/var/folders/*/*/T/playwright_firefoxdev_profile-*",
        "/var/folders/*/*/T/playwright_firefoxdev_profile-*",
    ]
    for pattern in patterns:
        dirs = glob.glob(pattern)
        if dirs:
            return sorted(dirs, key=os.path.getmtime)[-1]
    return None

def test():
    print("=== Testing keyword search fix ===\n")

    with Foxyz(headless=False) as browser:
        page = browser.new_page()
        page.goto("about:blank")

        # Detect profile early
        time.sleep(2)
        profile = get_profile_dir()
        if profile:
            print(f"Profile dir: {profile}")
        else:
            print("WARNING: Could not find profile directory")

        print("\nWaiting 25 seconds for search service initialization...")
        for i in range(25):
            time.sleep(1)
            if i % 5 == 4:
                if profile:
                    search_json = os.path.join(profile, "search.json.mozlz4")
                    exists = os.path.exists(search_json)
                    size = os.path.getsize(search_json) if exists else 0
                    print(f"  [{i+1}s] search.json.mozlz4: {'EXISTS (' + str(size) + ' bytes)' if exists else 'not yet'}")
                else:
                    print(f"  [{i+1}s] (no profile found yet)")
                    profile = get_profile_dir()

        # Final check
        if profile:
            search_json = os.path.join(profile, "search.json.mozlz4")
            if os.path.exists(search_json):
                print(f"\n✅ search.json.mozlz4 EXISTS ({os.path.getsize(search_json)} bytes)")
                print("   Search engines have been loaded by Firefox!")
            else:
                print(f"\n❌ search.json.mozlz4 NOT FOUND")
                print("   Search engines failed to load - check services.settings.server")

        # Test URL bar fixup via window.location navigation
        # Firefox FixupURI logic applies when window.location is set to a bare word
        print("\n--- Test: window.location = bare word ---")
        test_query = "foxyzuniquesearchtest44321"
        try:
            page.evaluate(f"window.location.href = '{test_query}'")
        except Exception as e:
            print(f"evaluate error: {str(e)[:100]}")

        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass
        time.sleep(2)
        url = page.url
        print(f"Current URL: {url}")

        if "google.com/search" in url:
            print("✅ KEYWORD SEARCH WORKS!")
        elif "neterror" in url or "about:neterror" in url:
            print("❌ Network error page - keyword search not working")
        elif "about:blank" in url:
            print("⚠ Still on about:blank")
        else:
            print(f"? Result: {url}")

        # Also check from about:blank with window.location
        print("\n--- Test: location.assign with multi-word (URL-encoded) ---")
        page.goto("about:blank")
        time.sleep(1)
        test_query2 = "foxyz weather today"
        try:
            # Spaces in URL will likely make Firefox use keyword search
            page.evaluate(f"window.location.href = 'foxyz weather today'")
        except Exception as e:
            print(f"evaluate error: {str(e)[:100]}")

        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass
        time.sleep(2)
        url2 = page.url
        print(f"Current URL: {url2}")

        if "google.com/search" in url2:
            print("✅ Multi-word keyword search WORKS!")
        elif "neterror" in url2:
            print("❌ Network error")
        else:
            print(f"? Result: {url2}")

        print("\n=== Press Ctrl+C to close ===")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    test()
