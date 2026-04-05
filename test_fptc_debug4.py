"""Debug Fptc constructor and instance methods."""
import json, time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.firefox.connect('ws://localhost:52460/737f814dcd2e9366ee01e23d7cafa5c4')
    ctx = browser.new_context()
    page = ctx.new_page()

    page.goto('https://pixelscan.net/fingerprint-check', wait_until='domcontentloaded', timeout=30000)
    time.sleep(8)

    # Deep inspection of Fptc instance from content world
    page.evaluate("""
        var rd = document.createElement('div');
        rd.id = '__fptest4';
        rd.style.display = 'none';
        document.body.appendChild(rd);

        var s = document.createElement('script');
        s.textContent = `
            (function() {
                var rd = document.getElementById('__fptest4');
                try {
                    // Check UAParser first
                    rd.dataset.uaparserType = typeof UAParser;
                    rd.dataset.topUaparser = typeof top.UAParser;

                    var parser;
                    try {
                        parser = new UAParser();
                        rd.dataset.parserResult = parser.getResult ? JSON.stringify(parser.getResult()).substring(0, 300) : 'no getResult';
                    } catch(e) {
                        rd.dataset.parserError = e.message;
                    }

                    // Now create Fptc
                    var fp = new Fptc();

                    // List all properties
                    var allProps = Object.getOwnPropertyNames(fp);
                    rd.dataset.instanceProps = JSON.stringify(allProps);

                    // Check which are functions
                    var funcs = allProps.filter(function(p) { return typeof fp[p] === 'function'; });
                    rd.dataset.functions = JSON.stringify(funcs);

                    // Check audio function specifically
                    rd.dataset.audioType = typeof fp.audio;
                    if (typeof fp.audio === 'function') {
                        rd.dataset.audioStr = fp.audio.toString().substring(0, 200);
                    }

                    rd.dataset.done = 'true';
                } catch(e) {
                    rd.dataset.error = e.message + ' | stack: ' + (e.stack || '').substring(0, 500);
                }
            })();
        `;
        document.body.appendChild(s);
    """)
    time.sleep(2)

    for key in ['uaparserType', 'topUaparser', 'parserResult', 'parserError',
                'instanceProps', 'functions', 'audioType', 'audioStr', 'done', 'error']:
        val = page.evaluate(f"document.getElementById('__fptest4')?.dataset?.{key} || ''")
        if val:
            print(f"  {key}: {val[:200]}")

    ctx.close()
    browser.close()
