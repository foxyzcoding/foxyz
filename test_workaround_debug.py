"""Debug: check if workaround triggers on pixelscan."""
import json, time
from foxyz import Foxyz

with Foxyz(headless=False) as browser:
    page = browser.new_page()

    # Add custom debug init_script BEFORE the Foxyz one
    page.context.add_init_script("""
        window.__iframeSrcLog = [];
        var origDesc = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'src');
        window.__origSrcDesc = origDesc;
        console.log('[WORKAROUND-DEBUG] Init script loaded, src descriptor exists: ' + !!origDesc);
    """)

    page.goto('https://pixelscan.net/fingerprint-check', wait_until='domcontentloaded', timeout=30000)
    time.sleep(10)

    # Check from content world what happened
    page.evaluate("""
        var rd = document.createElement('div');
        rd.id = '__wdebug';
        rd.style.display = 'none';
        document.body.appendChild(rd);

        var s = document.createElement('script');
        s.textContent = `
            var rd = document.getElementById('__wdebug');

            // Check if src setter is patched
            var desc = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'src');
            rd.dataset.srcSetterIsNative = (desc && desc.set && desc.set.toString().includes('native code')) ? 'native' : 'patched';
            rd.dataset.srcSetterStr = desc ? desc.set.toString().substring(0, 200) : 'no descriptor';

            // Check iframes on page
            var iframes = document.querySelectorAll('iframe');
            var iframeInfo = [];
            iframes.forEach(function(f) {
                iframeInfo.push({
                    src: (f.getAttribute('src') || '').substring(0, 80),
                    srcdoc: (f.getAttribute('srcdoc') || '').substring(0, 80),
                    class: f.className,
                });
            });
            rd.dataset.iframes = JSON.stringify(iframeInfo);

            // Check if Fptc and UAParser exist
            rd.dataset.fptc = typeof Fptc;
            rd.dataset.uaparser = typeof UAParser;
        `;
        document.body.appendChild(s);
    """)
    time.sleep(1)

    for key in ['srcSetterIsNative', 'srcSetterStr', 'iframes', 'fptc', 'uaparser']:
        val = page.evaluate(f"document.getElementById('__wdebug')?.dataset?.{key} || ''")
        print(f"{key}: {val[:300]}")
