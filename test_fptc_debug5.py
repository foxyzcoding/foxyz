"""Test Fptc collectors with Promise-based calling convention."""
import json, time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.firefox.connect('ws://localhost:52460/737f814dcd2e9366ee01e23d7cafa5c4')
    ctx = browser.new_context()
    page = ctx.new_page()

    page.goto('https://pixelscan.net/fingerprint-check', wait_until='domcontentloaded', timeout=30000)
    time.sleep(8)

    # Test collectors using Promise pattern (fp.xxx().then(...))
    page.evaluate("""
        var rd = document.createElement('div');
        rd.id = '__fptest5';
        rd.style.display = 'none';
        document.body.appendChild(rd);

        var s = document.createElement('script');
        s.textContent = `
            (async function() {
                var rd = document.getElementById('__fptest5');
                var fp = new Fptc();
                var results = {};
                var errors = {};

                var names = fp.functionsNames;
                for (var i = 0; i < names.length; i++) {
                    var name = names[i];
                    try {
                        var result = await Promise.race([
                            fp[name](),
                            new Promise(function(_, rej) { setTimeout(function() { rej(new Error('TIMEOUT_5s')); }, 5000); })
                        ]);
                        results[name] = typeof result === 'object' ? JSON.stringify(result).substring(0, 150) : String(result).substring(0, 150);
                    } catch(e) {
                        errors[name] = e.message.substring(0, 200);
                    }
                }
                rd.dataset.result = JSON.stringify({results: results, errors: errors});
            })();
        `;
        document.body.appendChild(s);
    """)

    # Wait for result
    for i in range(40):
        time.sleep(2)
        raw = page.evaluate("document.getElementById('__fptest5')?.dataset?.result || ''")
        if raw:
            data = json.loads(raw)
            print("Successful collectors:")
            for k, v in data.get('results', {}).items():
                print(f"  {k:25s}: {v[:100]}")
            if data.get('errors'):
                print("\nFailed collectors:")
                for k, v in data['errors'].items():
                    print(f"  {k:25s}: {v}")
            break
        if i % 5 == 0:
            print(f"[{(i+1)*2:3d}s] Waiting...")
    else:
        print("Timed out")

    ctx.close()
    browser.close()
