"""Test direct HTML injection via context.route() with debugging."""
import json, time, gzip, zlib
from foxyz import Foxyz
from foxyz.sync_api import _JSURL_IFRAME_FIX_SCRIPT

inject_log = []

with Foxyz(headless=False) as browser:
    ctx = browser.new_context()

    def handle(route):
        url = route.request.url
        path = url.split('?')[0].split('#')[0]
        dot = path.rfind('.')
        skip_exts = {'.js', '.css', '.png', '.jpg', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.gif', '.json', '.webp', '.map'}
        if dot != -1 and path[dot:].lower() in skip_exts:
            route.continue_()
            return
        try:
            response = route.fetch()
            ct = response.headers.get('content-type', '')
            if 'text/html' not in ct:
                route.fulfill(response=response)
                return

            raw = response.body()
            ce = response.headers.get('content-encoding', '')
            inject_log.append(f"HTML response: {url[:60]}, ce={ce}, raw_len={len(raw)}, first_bytes={raw[:4].hex()}")

            # Decompress based on content-encoding
            try:
                if ce == 'gzip' or raw[:2] == b'\x1f\x8b':
                    raw = gzip.decompress(raw)
                elif ce == 'zstd' or raw[:4] == b'\x28\xb5\x2f\xfd':
                    import zstandard
                    raw = zstandard.ZstdDecompressor().decompress(raw, max_output_size=len(raw) * 20)
                elif ce in ('br', 'brotli'):
                    import brotli
                    raw = brotli.decompress(raw)
                elif ce == 'deflate':
                    raw = zlib.decompress(raw)
            except Exception as e:
                inject_log.append(f"  Decompress error: {e}")
                route.fulfill(response=response)
                return

            body = raw.decode('utf-8', errors='replace')
            inject_log.append(f"  Decoded HTML: {len(body)} chars, has <head>: {'<head>' in body}")

            if '<head>' in body:
                body = body.replace('<head>', '<head>' + _JSURL_IFRAME_FIX_SCRIPT, 1)
            elif '<head ' in body:
                idx = body.index('<head ')
                close = body.index('>', idx)
                body = body[:close+1] + _JSURL_IFRAME_FIX_SCRIPT + body[close+1:]
            else:
                body = _JSURL_IFRAME_FIX_SCRIPT + body

            hdrs = {k: v for k, v in response.headers.items()
                    if k.lower() not in ('content-length', 'content-encoding')}
            route.fulfill(status=response.status, headers=hdrs, body=body)
            inject_log.append("  INJECTED!")
        except Exception as e:
            inject_log.append(f"ERROR: {e}")
            route.continue_()

    ctx.route("**/*", handle)

    page = ctx.new_page()
    page.goto('https://pixelscan.net/fingerprint-check', wait_until='domcontentloaded', timeout=90000)
    time.sleep(3)

    print(f"Route log ({len(inject_log)} entries):")
    for entry in inject_log:
        print(f"  {entry}")

    # Check
    page.evaluate("""
        var rd = document.createElement('div');
        rd.id = '__px3';
        rd.style.display = 'none';
        document.body.appendChild(rd);
        var s = document.createElement('script');
        s.textContent = "var d = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'src'); document.getElementById('__px3').dataset.native = d.set.toString().includes('native code') ? 'yes' : 'no';";
        document.body.appendChild(s);
    """)
    time.sleep(1)
    native = page.evaluate("document.getElementById('__px3')?.dataset?.native || 'N/A'")
    print(f"\nsrc setter patched: {'YES' if native == 'no' else 'NO'}")

    if native == 'no':
        print("\nWaiting for verdict...")
        for i in range(20):
            time.sleep(3)
            state = page.evaluate("""(function() {
                var body = document.body.innerText;
                var match = body.match(/Your Browser Fingerprint is (consistent|inconsistent)/i);
                return JSON.stringify({verdict: match ? match[1] : null, collecting: body.includes('Collecting Data')});
            })()""")
            s = json.loads(state)
            if s.get('verdict'):
                print(f"  [{(i+1)*3:3d}s] VERDICT: {s['verdict'].upper()}")
                break
            print(f"  [{(i+1)*3:3d}s] {'COLLECTING' if s['collecting'] else 'WAITING'}")
