"""Test javascript: URL iframe directly on pixelscan domain."""
import json, time
from foxyz import Foxyz

with Foxyz(headless=False) as browser:
    page = browser.new_page()
    page.goto('https://pixelscan.net/fingerprint-check', wait_until='domcontentloaded', timeout=60000)
    time.sleep(8)

    # Setup listener
    page.evaluate("""
        var rd = document.createElement('div');
        rd.id = '__jtest';
        rd.style.display = 'none';
        document.body.appendChild(rd);
        window.addEventListener('message', function(e) {
            if (e.data && e.data.source) {
                document.getElementById('__jtest').dataset[e.data.source] = e.data.value;
            }
        });
    """)

    # Test from content world via script tag
    page.evaluate("""
        var s = document.createElement('script');
        s.textContent = 'var f=document.createElement(\"iframe\");f.style.display=\"none\";f.src=\"javascript:parent.postMessage({source:\\'test1\\',value:\\'OK\\'},\\'*\\');void(0);\";document.body.appendChild(f);';
        document.body.appendChild(s);
    """)
    time.sleep(3)
    r1 = page.evaluate("document.getElementById('__jtest')?.dataset?.test1 || 'BLOCKED'")
    print(f"Content-world javascript: URL on pixelscan: {r1}")

    # Also try: append iframe WITHOUT src, then set src later
    page.evaluate("""
        var s2 = document.createElement('script');
        s2.textContent = 'var f2=document.createElement(\"iframe\");f2.style.display=\"none\";document.body.appendChild(f2);setTimeout(function(){f2.src=\"javascript:parent.postMessage({source:\\'test2\\',value:\\'OK2\\'},\\'*\\');void(0);\";},100);';
        document.body.appendChild(s2);
    """)
    time.sleep(3)
    r2 = page.evaluate("document.getElementById('__jtest')?.dataset?.test2 || 'BLOCKED'")
    print(f"Content-world iframe then set src: {r2}")

    # Try srcdoc approach directly
    page.evaluate("""
        var s3 = document.createElement('script');
        s3.textContent = 'var f3=document.createElement(\"iframe\");f3.style.display=\"none\";f3.srcdoc=\"<html><body><scr\"+\"ipt>parent.postMessage({source:\\'test3\\',value:\\'SRCDOC_OK\\'},\\'*\\')</scr\"+\"ipt></body></html>\";document.body.appendChild(f3);';
        document.body.appendChild(s3);
    """)
    time.sleep(3)
    r3 = page.evaluate("document.getElementById('__jtest')?.dataset?.test3 || 'BLOCKED'")
    print(f"Content-world srcdoc on pixelscan: {r3}")
