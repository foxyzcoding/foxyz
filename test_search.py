"""
Test keyword search from URL bar.
Checks search engine availability and keyword.enabled pref.
"""
from foxyz.sync_api import Foxyz, NewContext
import time
import json

def check_search_setup():
    print("=== Testing Foxyz keyword search setup ===")
    with Foxyz(headless=False) as browser:
        # Use NewContext to get a context
        from foxyz.sync_api import NewBrowser
        from playwright.sync_api import sync_playwright

        page = browser.new_page()

        # Check 1: keyword.enabled via about:config
        print("\n[1] Checking keyword.enabled...")
        page.goto("about:config")
        time.sleep(1)
        try:
            # Try to interact with about:config
            page.fill("input[id*='search'], input[placeholder*='Search']", "keyword.enabled")
            time.sleep(1)
            # Read the value shown
            content = page.content()
            if "keyword.enabled" in content:
                # Extract value
                if '"true"' in content or ">true<" in content or "true" in content:
                    print("  keyword.enabled = true ✓")
                elif '"false"' in content or ">false<" in content or "false" in content:
                    print("  keyword.enabled = false ✗ (needs fix!)")
                else:
                    print("  keyword.enabled: value unclear, checking URL fixup...")
        except Exception as e:
            print(f"  about:config error: {e}")

        # Check 2: search engines via about:preferences#search
        print("\n[2] Checking search engines...")
        page.goto("about:preferences#search")
        time.sleep(2)
        content = page.content()

        engines_found = []
        for engine in ["Google", "DuckDuckGo", "Bing", "None", "Yahoo"]:
            if engine in content:
                engines_found.append(engine)

        if engines_found:
            print(f"  Engines found in page: {engines_found}")
        else:
            print("  WARNING: No known engines found in preferences page!")

        # Check 3: check if browser.urlbar.maxRichResults is 0 (blocks heuristic results)
        print("\n[3] Checking browser.urlbar.maxRichResults...")
        page.goto("about:config")
        time.sleep(1)
        try:
            page.fill("input[id*='search'], input[placeholder*='Search']", "browser.urlbar.maxRichResults")
            time.sleep(1)
            content = page.content()
            if "browser.urlbar.maxRichResults" in content:
                # Try to get the value
                import re
                match = re.search(r'maxRichResults.*?(\d+)', content)
                if match:
                    val = int(match.group(1))
                    if val == 0:
                        print(f"  browser.urlbar.maxRichResults = 0 ✗ (BLOCKS keyword search results!)")
                    else:
                        print(f"  browser.urlbar.maxRichResults = {val} ✓")
        except Exception as e:
            print(f"  Error: {e}")

        # Check 4: Try actual keyword navigation via page.evaluate
        print("\n[4] Testing keyword search navigation...")
        page.goto("about:blank")
        time.sleep(1)
        try:
            # Use window.location to navigate with keyword: protocol
            page.goto("keyword:foxyz test search unique 98765")
            time.sleep(3)
            url = page.url
            print(f"  Result URL: {url}")
            if "google.com/search" in url:
                print("  ✅ SUCCESS: Keyword search works via keyword: protocol!")
            elif "error" in url.lower() or "about:neterror" in url:
                print("  ✗ FAILED: Got error page - likely no search engines")
            else:
                print(f"  ? Unknown result: {url}")
        except Exception as e:
            print(f"  keyword: navigation error: {e}")

        print("\n=== Done. Press Ctrl+C to close the browser. ===")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    check_search_setup()
