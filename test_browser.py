"""Launch Foxyz browser visually for testing layout."""
from foxyz import Foxyz
import time

with Foxyz(headless=False) as browser:
    page = browser.new_page()
    page.goto("https://www.google.com")
    print("Browser opened at google.com — check layout visually")
    print("Press Ctrl+C to close")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
