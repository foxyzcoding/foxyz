"""Debug: trace route handler execution."""
import json, time
from foxyz import Foxyz

route_log = []

with Foxyz(headless=False) as browser:
    page = browser.new_page()

    # Add a SECOND route handler to see if ANY route handlers fire
    def debug_route(route):
        rt = route.request.resource_type
        url = route.request.url[:60]
        route_log.append(f"{rt}: {url}")
        route.continue_()

    page.route("**/*", debug_route)

    page.goto('https://pixelscan.net/fingerprint-check', wait_until='domcontentloaded', timeout=90000)
    time.sleep(5)

    print(f"Route handler called {len(route_log)} times")
    for entry in route_log[:20]:
        print(f"  {entry}")
    if len(route_log) > 20:
        print(f"  ... and {len(route_log) - 20} more")
