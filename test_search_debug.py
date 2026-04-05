"""Check if our injected script is in the page DOM."""
import json, time
from foxyz import Foxyz

with Foxyz(headless=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto('https://pixelscan.net/fingerprint-check', wait_until='domcontentloaded', timeout=90000)
    time.sleep(8)

    result = page.evaluate("""(function() {
        var headHTML = document.head ? document.head.innerHTML : '';
        var hasMO = headHTML.includes('MutationObserver');
        var headScripts = document.head ? document.head.querySelectorAll('script').length : 0;
        return JSON.stringify({
            hasMutationObserver: hasMO,
            headScriptCount: headScripts,
            headFirst300: headHTML.substring(0, 300),
        });
    })()""")
    data = json.loads(result)
    print(f"Has MutationObserver in head: {data['hasMutationObserver']}")
    print(f"Head script count: {data['headScriptCount']}")
    print(f"Head first 300 chars:")
    print(data['headFirst300'])
