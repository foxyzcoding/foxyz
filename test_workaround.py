"""Test javascript: URL iframe workaround from content world."""
import json, time
from foxyz import Foxyz

with Foxyz(headless=False) as browser:
    page = browser.new_page()
    page.goto('data:text/html,<h1>Test</h1>')
    time.sleep(1)

    # Set up listener and test via content-world script tag
    page.evaluate("""
        var rd = document.createElement('div');
        rd.id = '__itest';
        document.body.appendChild(rd);
        window.addEventListener('message', function(e) {
            if (e.data && e.data.source) {
                document.getElementById('__itest').dataset[e.data.source] = e.data.value;
            }
        });
    """)

    # Create iframe via content-world script tag (NOT evaluate)
    page.evaluate("""
        var s = document.createElement('script');
        s.textContent = `
            var iframe = document.createElement('iframe');
            iframe.src = "javascript:parent.postMessage({source:'jsurl',value:'WORKS'},'*');void(0);";
            iframe.style.display = 'none';
            document.body.appendChild(iframe);
        `;
        document.body.appendChild(s);
    """)
    time.sleep(3)

    # Check result
    r = page.evaluate("document.getElementById('__itest')?.dataset?.jsurl || 'BLOCKED'")
    print(f"Content-world javascript: URL iframe: {r}")

    # Also check: did the iframe get srcdoc instead?
    iframe_info = page.evaluate("""(function() {
        var iframes = document.querySelectorAll('iframe');
        var info = [];
        iframes.forEach(function(f) {
            info.push({
                src: f.src,
                srcdoc: (f.srcdoc || '').substring(0, 200),
                hasSrcdoc: !!f.srcdoc,
            });
        });
        return JSON.stringify(info);
    })()""")
    print(f"Iframe info: {iframe_info}")

    if r == 'WORKS':
        # Test pixelscan!
        print("\n=== PIXELSCAN TEST ===")
        page.goto('https://pixelscan.net/fingerprint-check', wait_until='domcontentloaded', timeout=30000)

        for i in range(20):
            time.sleep(3)
            state = page.evaluate("""(function() {
                var body = document.body ? document.body.innerText : '';
                return JSON.stringify({
                    collecting: body.includes('Collecting'),
                    consistent: body.includes('onsistent'),
                });
            })()""")
            s = json.loads(state)
            if s['consistent']:
                verdict = page.evaluate("""(function() {
                    var body = document.body.innerText;
                    var idx = body.indexOf('onsistent');
                    return body.substring(Math.max(0,idx-30), idx+50);
                })()""")
                print(f"  [{(i+1)*3:3d}s] VERDICT: {verdict}")
                break
            status = 'COLLECTING' if s['collecting'] else 'UNKNOWN'
            print(f"  [{(i+1)*3:3d}s] {status}")
        else:
            print("  No verdict after 60s")
