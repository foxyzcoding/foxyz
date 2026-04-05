"""Test each FPTC collector individually with short timeouts."""
import json, time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.firefox.connect('ws://localhost:52460/737f814dcd2e9366ee01e23d7cafa5c4')
    ctx = browser.new_context()
    page = ctx.new_page()

    page.goto('https://pixelscan.net/fingerprint-check', wait_until='domcontentloaded', timeout=30000)
    time.sleep(8)

    # Test each collector one at a time with 3s timeout
    collectors = [
        'audio', 'canvasHash', 'fonts', 'hardwareConcurrency',
        'language', 'navigatorPlatform', 'screenResolution',
        'secCh', 'timezone', 'ua', 'webDriver', 'webglHash', 'webglMeta'
    ]

    for name in collectors:
        page.evaluate(f"""
            var rd = document.getElementById('__fptest_{name}');
            if (rd) rd.remove();
            rd = document.createElement('div');
            rd.id = '__fptest_{name}';
            rd.style.display = 'none';
            document.body.appendChild(rd);

            var s = document.createElement('script');
            s.textContent = `
                (async function() {{
                    var rd = document.getElementById('__fptest_{name}');
                    try {{
                        var fp = new Fptc();
                        var timer = setTimeout(function() {{
                            rd.dataset.result = 'TIMEOUT';
                        }}, 3000);
                        fp['{name}'](function(val) {{
                            clearTimeout(timer);
                            rd.dataset.result = typeof val === 'object' ? JSON.stringify(val).substring(0, 200) : String(val).substring(0, 200);
                        }});
                    }} catch(e) {{
                        rd.dataset.result = 'ERROR: ' + e.message;
                    }}
                }})();
            `;
            document.body.appendChild(s);
        """)
        time.sleep(4)
        result = page.evaluate(f"document.getElementById('__fptest_{name}')?.dataset?.result || 'PENDING'")
        status = "OK" if result not in ('TIMEOUT', 'PENDING') else result
        if status == "OK":
            print(f"  {name:25s} OK: {result[:80]}")
        else:
            print(f"  {name:25s} **{status}**")

    ctx.close()
    browser.close()
