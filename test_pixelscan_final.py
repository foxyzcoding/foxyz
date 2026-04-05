"""Final pixelscan test with proper verdict detection."""
import json, time
from foxyz import Foxyz

with Foxyz(headless=False) as browser:
    page = browser.new_page()

    print("=== PIXELSCAN FINGERPRINT TEST ===")
    page.goto('https://pixelscan.net/fingerprint-check', wait_until='domcontentloaded', timeout=30000)

    for i in range(30):
        time.sleep(3)
        state = page.evaluate("""(function() {
            var body = document.body ? document.body.innerText : '';
            var verdictMatch = body.match(/Your Browser Fingerprint is (consistent|inconsistent)/i);
            var verdict = verdictMatch ? verdictMatch[1] : null;
            var collecting = body.includes('Collecting Data');
            var scanning = body.includes('is scanning');

            // Get card statuses
            var fingerprint = body.includes('Masking detected') ? 'masking' :
                              body.includes('No masking detected') ? 'clean' :
                              body.includes('Collecting Data') ? 'loading' : 'unknown';

            return JSON.stringify({
                verdict: verdict,
                collecting: collecting,
                scanning: scanning,
            });
        })()""")
        s = json.loads(state)
        elapsed = (i+1)*3

        if s.get('verdict'):
            print(f"  [{elapsed:3d}s] VERDICT: {s['verdict'].upper()}")
            # Get full summary
            summary = page.evaluate("""(function() {
                var body = document.body.innerText;
                // Extract key info
                var lines = body.split('\\n').filter(function(l) { return l.trim().length > 0; });
                var info = [];
                for (var l of lines) {
                    l = l.trim();
                    if (l.includes('Masking') || l.includes('masking') ||
                        l.includes('No automated') || l.includes('automated') ||
                        l.includes('on Windows') || l.includes('on Mac') ||
                        l.includes('proxy detected') || l.includes('Fingerprint is')) {
                        info.push(l);
                    }
                }
                return info.join(' | ');
            })()""")
            print(f"  Summary: {summary[:300]}")
            break

        status = 'SCANNING' if s['scanning'] else ('COLLECTING' if s['collecting'] else 'WAITING')
        print(f"  [{elapsed:3d}s] {status}")
    else:
        print("  No verdict after 90s — still stuck")
        page_text = page.evaluate("document.body.innerText.substring(0, 800)")
        print(f"  Page text:\n{page_text[:500]}")
