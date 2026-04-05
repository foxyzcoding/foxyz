"""Get detailed error from canvasHash and webglHash collectors."""
import json, time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.firefox.connect('ws://localhost:52460/737f814dcd2e9366ee01e23d7cafa5c4')
    ctx = browser.new_context()
    page = ctx.new_page()

    page.goto('https://pixelscan.net/fingerprint-check', wait_until='load', timeout=30000)
    time.sleep(10)

    page.evaluate("""
        var rd = document.createElement('div');
        rd.id = '__fptest6';
        rd.style.display = 'none';
        document.body.appendChild(rd);

        var s = document.createElement('script');
        s.textContent = `
            (async function() {
                var rd = document.getElementById('__fptest6');
                var fp = new Fptc();

                // Get canvasHash source
                rd.dataset.canvasHashSrc = fp.canvasHash.toString().substring(0, 500);

                // Get _canvasHash source (note: there's a _canvasHash property)
                if (typeof fp._canvasHash === 'function') {
                    rd.dataset.internalCanvasHashSrc = fp._canvasHash.toString().substring(0, 500);
                } else {
                    rd.dataset.internalCanvasHash = typeof fp._canvasHash + ': ' + JSON.stringify(fp._canvasHash).substring(0, 200);
                }

                // Try canvasHash with detailed error capture
                try {
                    var result = await Promise.race([
                        fp.canvasHash(),
                        new Promise(function(_, rej) { setTimeout(function() { rej(new Error('TIMEOUT')); }, 5000); })
                    ]);
                    rd.dataset.canvasResult = String(result).substring(0, 200);
                } catch(e) {
                    rd.dataset.canvasError = e.message;
                    rd.dataset.canvasStack = (e.stack || '').substring(0, 1000);
                }

                // Try webglHash
                try {
                    var result2 = await Promise.race([
                        fp.webglHash(),
                        new Promise(function(_, rej) { setTimeout(function() { rej(new Error('TIMEOUT')); }, 5000); })
                    ]);
                    rd.dataset.webglResult = String(result2).substring(0, 200);
                } catch(e) {
                    rd.dataset.webglError = e.message;
                    rd.dataset.webglStack = (e.stack || '').substring(0, 1000);
                }
            })();
        `;
        document.body.appendChild(s);
    """)
    time.sleep(8)

    for key in ['canvasHashSrc', 'internalCanvasHashSrc', 'internalCanvasHash',
                'canvasResult', 'canvasError', 'canvasStack',
                'webglResult', 'webglError', 'webglStack']:
        val = page.evaluate(f"document.getElementById('__fptest6')?.dataset?.{key} || ''")
        if val:
            print(f"{key}:")
            print(f"  {val[:300]}")
            print()

    ctx.close()
    browser.close()
