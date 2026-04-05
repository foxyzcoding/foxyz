from foxyz.sync_api import Foxyz

ACCEPT_ENCODING = "identity"

with Foxyz(headless=False) as browser:
    page = browser.new_page(extra_http_headers={"accept-encoding": ACCEPT_ENCODING})
    page.goto("https://abrahamjuliot.github.io/creepjs/")
    input("Press Enter to close...")
