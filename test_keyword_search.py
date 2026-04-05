"""
Final verification: Test URL bar keyword search using AppleScript to interact with browser chrome.
"""
from foxyz.sync_api import Foxyz
import time
import subprocess
import glob
import os

def test():
    print("=== Final Keyword Search Verification ===\n")

    with Foxyz(headless=False) as browser:
        page = browser.new_page()
        page.goto("about:blank")
        time.sleep(5)

        # Check search.json.mozlz4
        profiles = glob.glob('/private/var/folders/5v/qkphphxx55bbwp0y3v84wmw00000gn/T/playwright_firefoxdev_profile-*')
        if profiles:
            profile = sorted(profiles, key=os.path.getmtime)[-1]
            search_json = os.path.join(profile, "search.json.mozlz4")
            if os.path.exists(search_json):
                print(f"✅ search.json.mozlz4 EXISTS ({os.path.getsize(search_json)} bytes)")
            else:
                print("❌ search.json.mozlz4 missing")
                return

        print("\nUsing AppleScript to type in URL bar...")
        # Use AppleScript to type in Firefox URL bar
        script = '''
        tell application "System Events"
            tell process "camoufox"
                set frontmost to true
            end tell
            delay 0.8

            -- Press Cmd+L to focus URL bar
            keystroke "l" using {command down}
            delay 0.8

            -- Select all and type search query
            keystroke "a" using {command down}
            delay 0.3
            keystroke "foxyzuniquesearchtest99887766"
            delay 0.5

            -- Press Enter
            key code 36
        end tell
        return "done"
        '''

        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        print(f"AppleScript result: {result.stdout.strip()} | err: {result.stderr.strip()[:100]}")

        # Wait for navigation
        time.sleep(4)
        url = page.url
        print(f"\nResult URL: {url}")

        if "google.com/search" in url:
            print("✅ SUCCESS! URL bar keyword search WORKS! Google search triggered!")
            if "foxyzuniquesearchtest99887766" in url or "foxyzuniquesearchtest" in url:
                print("✅ Correct query in URL too!")
        elif "neterror" in url or "about:neterror" in url:
            print("❌ Got network error page - treated as hostname")
        elif "about:blank" in url:
            print("⚠ Still on about:blank - AppleScript may have failed")
        else:
            print(f"? Result: {url}")

        print("\n=== Ctrl+C to close ===")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    test()
