"""Test if srcdoc iframe can access top.Fptc from content world."""
import json, time, base64
from foxyz import Foxyz

with Foxyz(headless=False) as browser:
    page = browser.new_page()
    page.goto('https://pixelscan.net/fingerprint-check', wait_until='domcontentloaded', timeout=90000)
    time.sleep(10)

    # Set up message listener
    page.evaluate("""
        window.__topCheckResult = null;
        window.addEventListener('message', function(e) {
            if (e.data && e.data.source === 'topcheck') {
                window.__topCheckResult = e.data;
            }
        });
    """)

    # Create srcdoc test iframe via content-world script tag
    test_code = """
try {
    var r = {source: 'topcheck'};
    r.fptcType = typeof top.Fptc;
    r.uaparserType = typeof top.UAParser;
    if (typeof top.Fptc === 'function') {
        r.fptcSourceLen = top.Fptc.toString().length;
    }
    if (typeof top.UAParser === 'function') {
        var p = new top.UAParser();
        r.parserOK = !!p.getResult;
    }
    parent.postMessage(r, '*');
} catch(e) {
    parent.postMessage({source: 'topcheck', error: e.message, stack: (e.stack||'').substring(0, 300)}, '*');
}
"""
    b64_code = base64.b64encode(test_code.encode()).decode()

    page.evaluate(f"""
        var s = document.createElement('script');
        s.textContent = 'var f = document.createElement("iframe"); f.style.display = "none"; f.srcdoc = "<html><body><scr" + "ipt>eval(atob(\\'{b64_code}\\'))</scr" + "ipt></body></html>"; document.body.appendChild(f);';
        document.body.appendChild(s);
    """)
    time.sleep(3)

    # Check result (from Juggler context, but __topCheckResult was set from content world)
    result = page.evaluate("JSON.stringify(window.__topCheckResult)")
    print(f"Result: {result}")

    # Also check via data attribute
    page.evaluate("""
        var s2 = document.createElement('script');
        s2.textContent = 'document.body.dataset.topcheck = JSON.stringify(window.__topCheckResult || "null")';
        document.body.appendChild(s2);
    """)
    time.sleep(1)
    r2 = page.evaluate("document.body.dataset.topcheck || 'NOT SET'")
    print(f"Content world result: {r2}")
