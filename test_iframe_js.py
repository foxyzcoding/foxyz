"""Test if javascript: URL iframes execute code in Foxyz."""
import json, time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.firefox.connect('ws://localhost:52460/737f814dcd2e9366ee01e23d7cafa5c4')
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto('about:blank')
    time.sleep(1)

    # Test 1: Create a simple javascript: iframe
    page.evaluate("""
        var rd = document.createElement('div');
        rd.id = '__iframetest';
        rd.style.display = 'none';
        document.body.appendChild(rd);

        // Test 1: javascript: URL iframe
        var iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = "javascript:parent.document.getElementById('__iframetest').dataset.test1 = 'EXECUTED';void(0);";
        document.body.appendChild(iframe);

        // Test 2: javascript: URL with postMessage
        var iframe2 = document.createElement('iframe');
        iframe2.style.display = 'none';
        iframe2.src = "javascript:parent.postMessage({source:'iframeTest2',value:'OK'},'*');void(0);";
        document.body.appendChild(iframe2);

        // Listen for messages
        window.addEventListener('message', function(e) {
            if (e.data && e.data.source === 'iframeTest2') {
                document.getElementById('__iframetest').dataset.test2 = e.data.value;
            }
        });
    """)
    time.sleep(3)

    test1 = page.evaluate("document.getElementById('__iframetest')?.dataset?.test1 || 'NOT EXECUTED'")
    test2 = page.evaluate("document.getElementById('__iframetest')?.dataset?.test2 || 'NOT RECEIVED'")
    print(f"Test 1 (javascript: URL sets data attr): {test1}")
    print(f"Test 2 (javascript: URL with postMessage): {test2}")

    # Test 3: javascript: URL with base64-encoded eval (like pixelscan)
    import base64
    code = "(function(){parent.postMessage({source:'iframeTest3',value:'BASE64_OK'},'*');}())"
    b64 = base64.b64encode(code.encode()).decode()

    page.evaluate(f"""
        var iframe3 = document.createElement('iframe');
        iframe3.style.display = 'none';
        iframe3.src = "javascript:eval(atob('{b64}'))";
        document.body.appendChild(iframe3);

        window.addEventListener('message', function(e) {{
            if (e.data && e.data.source === 'iframeTest3') {{
                document.getElementById('__iframetest').dataset.test3 = e.data.value;
            }}
        }});
    """)
    time.sleep(3)

    test3 = page.evaluate("document.getElementById('__iframetest')?.dataset?.test3 || 'NOT RECEIVED'")
    print(f"Test 3 (javascript: URL with eval+atob like pixelscan): {test3}")

    # Test 4: Check if there are Firefox prefs blocking javascript: iframes
    print("\nChecking firefox preferences that might affect javascript: URLs...")
    result = page.evaluate("""(function() {
        // Check security.checkloaduri
        // We can't read Firefox prefs from content, but we can test behavior
        var tests = {};

        // Test with srcdoc instead
        var iframe4 = document.createElement('iframe');
        iframe4.style.display = 'none';
        iframe4.srcdoc = '<script>parent.postMessage({source:"iframeTest4",value:"SRCDOC_OK"},"*")</' + 'script>';
        document.body.appendChild(iframe4);

        return 'srcdoc test created';
    })()""")
    print(f"  {result}")

    page.evaluate("""
        window.addEventListener('message', function(e) {
            if (e.data && e.data.source === 'iframeTest4') {
                document.getElementById('__iframetest').dataset.test4 = e.data.value;
            }
        });
    """)
    time.sleep(3)

    test4 = page.evaluate("document.getElementById('__iframetest')?.dataset?.test4 || 'NOT RECEIVED'")
    print(f"Test 4 (srcdoc iframe with script): {test4}")

    ctx.close()
    browser.close()
