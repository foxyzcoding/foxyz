"""Test pixelscan with HTML injection workaround."""
import json, time
from foxyz import Foxyz

with Foxyz(headless=False) as browser:
    page = browser.new_page()
    print("Navigating to pixelscan.net...")
    page.goto('https://pixelscan.net/fingerprint-check', wait_until='domcontentloaded', timeout=90000)
    print("Page loaded!")
    time.sleep(5)

    # Check if iframe workaround is active in content world
    page.evaluate("""
        var rd = document.createElement('div');
        rd.id = '__px';
        rd.style.display = 'none';
        document.body.appendChild(rd);
        var s = document.createElement('script');
        s.textContent = "var d = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'src'); document.getElementById('__px').dataset.native = d.set.toString().includes('native code') ? 'yes' : 'no';";
        document.body.appendChild(s);
    """)
    time.sleep(1)
    native = page.evaluate("document.getElementById('__px')?.dataset?.native || 'N/A'")
    print(f"src setter patched: {'YES' if native == 'no' else 'NO'} (native={native})")

    print("\nWaiting for verdict...")
    for i in range(30):
        time.sleep(3)
        state = page.evaluate("""(function() {
            var body = document.body.innerText;
            var match = body.match(/Your Browser Fingerprint is (consistent|inconsistent)/i);
            return JSON.stringify({
                verdict: match ? match[1] : null,
                collecting: body.includes('Collecting Data'),
            });
        })()""")
        s = json.loads(state)
        if s.get('verdict'):
            print(f"  [{(i+1)*3:3d}s] VERDICT: {s['verdict'].upper()}")
            break
        status = 'COLLECTING' if s['collecting'] else 'WAITING'
        print(f"  [{(i+1)*3:3d}s] {status}")
    else:
        print("  Still no verdict after 90s")
