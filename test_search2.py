"""
Minimal test: check if keyword search works via keyword: URI scheme.
"""
from foxyz.sync_api import Foxyz
import time

def test():
    print("Testing keyword search...")
    with Foxyz(headless=False) as browser:
        page = browser.new_page()
        page.goto("about:blank")
        time.sleep(1)

        # Test 1: keyword: URI - should trigger search engine
        print("\nTest 1: goto keyword:foxyzuniquetest12345")
        try:
            page.goto("keyword:foxyzuniquetest12345", wait_until="load", timeout=8000)
        except Exception:
            pass
        url = page.url
        print(f"  Result URL: {url}")
        if "google.com/search" in url:
            print("  ✅ Keyword search WORKS! Google is the default engine.")
        elif "about:neterror" in url or "neterror" in url:
            print("  ❌ Got error page - NO SEARCH ENGINES configured")
        else:
            print(f"  ? Result: {url}")

        time.sleep(2)

        # Test 2: Try navigate to a clearly non-URL word
        # We can test this by catching the URL after navigation
        print("\nTest 2: navigate to 'foxyzuniquetest99999' as URL")
        try:
            page.goto("http://foxyzuniquetest99999/", wait_until="domcontentloaded", timeout=5000)
        except Exception:
            pass
        url2 = page.url
        print(f"  Result URL: {url2}")

        print("\n=== Press Ctrl+C to exit ===")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    test()
