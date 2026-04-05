"""Run the exact pixelscan iframe code in a test srcdoc iframe."""
import json, time, base64
from foxyz import Foxyz

# The EXACT code from pixelscan's iframe (decoded from base64)
FPTC_IFRAME_CODE = """(function (){
    try {
        eval(top.Fptc.toString().replace('function ()','function Fptc()').replace('function()','function Fptc()'));
        fp=new Fptc();
        fp.getFingerprints().then(f=>{
            parent.postMessage({messageSource:'fpCollect',value:f},'*')
        }).catch(e=>{
            parent.postMessage({messageSource:'fpError',error:e.message,stack:(e.stack||'').substring(0,500)},'*')
        });
    } catch(e) {
        parent.postMessage({messageSource:'fpError',error:e.message,stack:(e.stack||'').substring(0,500)},'*');
    }
}())"""

with Foxyz(headless=False) as browser:
    page = browser.new_page()
    page.goto('https://pixelscan.net/fingerprint-check', wait_until='domcontentloaded', timeout=90000)
    time.sleep(10)

    # Set up message listener
    page.evaluate("""
        window.__fpResults = [];
        window.addEventListener('message', function(e) {
            if (e.data && (e.data.messageSource === 'fpCollect' || e.data.messageSource === 'fpError')) {
                window.__fpResults.push(e.data);
            }
        });
    """)

    # Create test srcdoc iframe with the exact FPTC code
    b64 = base64.b64encode(FPTC_IFRAME_CODE.encode()).decode()
    page.evaluate(f"""
        var s = document.createElement('script');
        s.textContent = 'var f = document.createElement("iframe"); f.style.display="none"; f.srcdoc = "<html><body><scr" + "ipt>eval(atob(\\'{b64}\\'))</scr" + "ipt></body></html>"; document.body.appendChild(f);';
        document.body.appendChild(s);
    """)

    # Wait and check results
    for i in range(10):
        time.sleep(2)
        results = page.evaluate("JSON.stringify(window.__fpResults)")
        data = json.loads(results)
        if data:
            for r in data:
                if r.get('messageSource') == 'fpCollect':
                    value = r.get('value', {})
                    print(f"fpCollect received! Keys: {list(value.keys()) if isinstance(value, dict) else 'not dict'}")
                    if isinstance(value, dict):
                        for k, v in value.items():
                            vstr = str(v)[:100] if v else 'null'
                            print(f"  {k}: {vstr}")
                elif r.get('messageSource') == 'fpError':
                    print(f"fpError: {r.get('error')}")
                    print(f"Stack: {r.get('stack', '')[:300]}")
            break
    else:
        print("No fpCollect/fpError message received after 20s")
        # Check if there are any messages at all
        all_msgs = page.evaluate("JSON.stringify(window.__fpResults)")
        print(f"All messages: {all_msgs}")
