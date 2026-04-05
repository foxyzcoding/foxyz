#!/usr/bin/env python3
"""
Thorough fingerprint audit on pixelscan.net using Foxyz browser.
Extracts all detection results and runs consistency tests.
"""

import time
import json
import sys

from foxyz import Foxyz


def run_audit():
    print("=" * 80)
    print("FOXYZ FINGERPRINT AUDIT ON PIXELSCAN.NET")
    print("=" * 80)

    with Foxyz(headless=False) as browser:
        context = browser.new_context()
        page = context.new_page()

        # ── 1. Navigate to pixelscan ──
        print("\n[1] Navigating to pixelscan.net/fingerprint-check ...")
        page.goto("https://pixelscan.net/fingerprint-check", wait_until="domcontentloaded", timeout=60000)
        print("    Page loaded.")

        # ── 2. Wait for verdict to appear ──
        print("\n[2] Waiting for verdict (polling every 3s, max 90s) ...")
        verdict_text = None
        start = time.time()
        while time.time() - start < 90:
            # Try multiple selectors that pixelscan uses
            verdict_text = page.evaluate("""() => {
                // Look for verdict/status elements
                const selectors = [
                    '.fingerprint-verdict',
                    '.verdict',
                    '[class*="verdict"]',
                    '[class*="Verdict"]',
                    '[class*="status"]',
                    '[class*="result"]',
                    '.scan-result',
                    '#result',
                    '.fp-result',
                ];
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    if (els.length > 0) {
                        return Array.from(els).map(e => ({
                            selector: sel,
                            text: e.innerText?.trim(),
                            className: e.className,
                            id: e.id
                        })).filter(e => e.text);
                    }
                }
                return null;
            }""")

            # Also check if the body text contains known verdict phrases
            body_text = page.evaluate("() => document.body?.innerText || ''")
            has_verdict = any(phrase in body_text for phrase in [
                "Masking detected",
                "No masking detected",
                "Consistent",
                "Inconsistent",
                "threat",
                "Bot detected",
                "Human",
                "fingerprint check complete",
                "Your browser fingerprint"
            ])

            if has_verdict or (verdict_text and len(verdict_text) > 0):
                elapsed = time.time() - start
                print(f"    Verdict detected after {elapsed:.1f}s")
                break

            time.sleep(3)
            elapsed = time.time() - start
            print(f"    ... {elapsed:.0f}s elapsed, still waiting")
        else:
            print("    WARNING: Timed out waiting for verdict!")

        # Give extra time for all cards to render
        print("    Waiting 10s extra for all cards to fully render ...")
        time.sleep(10)

        # ── 3. Extract full page text ──
        print("\n[3] Extracting full page text ...")
        full_text = page.evaluate("() => document.body.innerText")
        print("\n--- FULL PAGE TEXT ---")
        print(full_text)
        print("--- END FULL PAGE TEXT ---\n")

        # ── 4. Extract structured card data ──
        print("\n[4] Extracting structured card/section data ...")
        cards_data = page.evaluate("""() => {
            const results = [];

            // Get all elements that look like cards/sections
            const allEls = document.querySelectorAll('div, section, article, tr, li');
            const seen = new Set();

            for (const el of allEls) {
                const text = el.innerText?.trim();
                if (!text || text.length > 2000 || text.length < 5) continue;
                if (seen.has(text)) continue;

                // Look for elements containing status keywords
                const hasStatus = /masking|consistent|inconsistent|detected|spoofed|mismatch|threat|bot|human|pass|fail|warn/i.test(text);
                if (hasStatus && text.split('\\n').length <= 15) {
                    seen.add(text);
                    results.push({
                        tag: el.tagName,
                        className: el.className?.toString()?.substring(0, 200),
                        text: text,
                        dataset: Object.assign({}, el.dataset)
                    });
                }
            }
            return results;
        }""")

        print(f"\n--- DETECTED STATUS CARDS ({len(cards_data)} found) ---")
        for i, card in enumerate(cards_data):
            print(f"\n  Card #{i+1}:")
            print(f"    Tag: {card['tag']}")
            print(f"    Class: {card['className']}")
            print(f"    Text: {card['text']}")
            if card.get('dataset'):
                print(f"    Dataset: {json.dumps(card['dataset'])}")
        print("--- END STATUS CARDS ---\n")

        # ── 5. Extract all data attributes and hidden elements ──
        print("\n[5] Extracting data attributes and hidden detection data ...")
        hidden_data = page.evaluate("""() => {
            const results = [];

            // Elements with data-* attributes related to fingerprinting
            const allEls = document.querySelectorAll('[data-result], [data-status], [data-score], [data-verdict], [data-test], [data-check]');
            for (const el of allEls) {
                results.push({
                    tag: el.tagName,
                    dataset: Object.assign({}, el.dataset),
                    text: el.innerText?.trim()?.substring(0, 500),
                    hidden: el.offsetParent === null
                });
            }

            // Also look for hidden elements with content
            const hiddenEls = document.querySelectorAll('[style*="display: none"], [style*="display:none"], [hidden], .hidden, .d-none');
            for (const el of hiddenEls) {
                const text = el.innerText?.trim();
                if (text && text.length > 5 && text.length < 2000) {
                    results.push({
                        tag: el.tagName,
                        className: el.className?.toString()?.substring(0, 200),
                        text: text,
                        isHidden: true
                    });
                }
            }

            // Check for JSON data in script tags
            const scripts = document.querySelectorAll('script[type="application/json"], script[type="application/ld+json"]');
            for (const s of scripts) {
                results.push({
                    tag: 'SCRIPT',
                    type: s.type,
                    content: s.textContent?.substring(0, 2000)
                });
            }

            // Look for __NEXT_DATA__ or similar hydration data
            const nextData = document.getElementById('__NEXT_DATA__');
            if (nextData) {
                results.push({
                    tag: 'NEXT_DATA',
                    content: nextData.textContent?.substring(0, 5000)
                });
            }

            // Check window variables
            const windowVars = {};
            for (const key of ['__fingerprint', '__result', '__scan', 'scanResult', 'fpData']) {
                if (window[key]) {
                    windowVars[key] = JSON.stringify(window[key]).substring(0, 2000);
                }
            }
            if (Object.keys(windowVars).length > 0) {
                results.push({ tag: 'WINDOW_VARS', data: windowVars });
            }

            return results;
        }""")

        print(f"\n--- HIDDEN/DATA ELEMENTS ({len(hidden_data)} found) ---")
        for i, item in enumerate(hidden_data):
            print(f"\n  Item #{i+1}: {json.dumps(item, indent=4, default=str)[:1000]}")
        print("--- END HIDDEN DATA ---\n")

        # ── 6. Fingerprint consistency tests ──
        print("\n[6] Running fingerprint consistency tests in browser ...")

        consistency_results = page.evaluate("""() => {
            const results = {};

            // ── Canvas fingerprint consistency ──
            try {
                function getCanvasFP() {
                    const canvas = document.createElement('canvas');
                    canvas.width = 200;
                    canvas.height = 50;
                    const ctx = canvas.getContext('2d');
                    ctx.textBaseline = 'top';
                    ctx.font = '14px Arial';
                    ctx.fillStyle = '#f60';
                    ctx.fillRect(0, 0, 200, 50);
                    ctx.fillStyle = '#069';
                    ctx.fillText('Foxyz fingerprint test! 🦊', 2, 15);
                    ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
                    ctx.fillRect(75, 1, 100, 25);
                    ctx.arc(50, 50, 50, 0, Math.PI * 2, true);
                    ctx.stroke();
                    return canvas.toDataURL();
                }
                const fp1 = getCanvasFP();
                const fp2 = getCanvasFP();
                const fp3 = getCanvasFP();
                results.canvas = {
                    consistent: fp1 === fp2 && fp2 === fp3,
                    fp1_prefix: fp1.substring(0, 80),
                    fp2_prefix: fp2.substring(0, 80),
                    fp3_prefix: fp3.substring(0, 80),
                    fp1_length: fp1.length,
                    fp2_length: fp2.length,
                    all_same: fp1 === fp2 && fp2 === fp3,
                    note: fp1 === fp2 ? "Canvas is stable across calls" : "Canvas VARIES between calls (noise injection detected)"
                };
            } catch (e) {
                results.canvas = { error: e.message };
            }

            // ── WebGL fingerprint consistency ──
            try {
                function getWebGLFP() {
                    const canvas = document.createElement('canvas');
                    const gl = canvas.getContext('webgl');
                    if (!gl) return 'no-webgl';
                    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                    return {
                        vendor: debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : 'n/a',
                        renderer: debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : 'n/a',
                        glVendor: gl.getParameter(gl.VENDOR),
                        glRenderer: gl.getParameter(gl.RENDERER),
                        glVersion: gl.getParameter(gl.VERSION),
                        shadingVersion: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
                    };
                }
                const wgl1 = getWebGLFP();
                const wgl2 = getWebGLFP();
                results.webgl = {
                    run1: wgl1,
                    run2: wgl2,
                    consistent: JSON.stringify(wgl1) === JSON.stringify(wgl2)
                };
            } catch (e) {
                results.webgl = { error: e.message };
            }

            // ── AudioContext fingerprint consistency ──
            try {
                results.audioContext = {};
                const ctx1 = new (window.AudioContext || window.webkitAudioContext)();
                const ctx2 = new (window.AudioContext || window.webkitAudioContext)();
                results.audioContext.sampleRate1 = ctx1.sampleRate;
                results.audioContext.sampleRate2 = ctx2.sampleRate;
                results.audioContext.sampleRateConsistent = ctx1.sampleRate === ctx2.sampleRate;
                results.audioContext.baseLatency1 = ctx1.baseLatency;
                results.audioContext.baseLatency2 = ctx2.baseLatency;
                results.audioContext.state1 = ctx1.state;
                results.audioContext.destination1Channels = ctx1.destination.maxChannelCount;
                results.audioContext.destination2Channels = ctx2.destination.maxChannelCount;
                ctx1.close();
                ctx2.close();
            } catch (e) {
                results.audioContext = { error: e.message };
            }

            // ── Navigator properties ──
            try {
                results.navigator = {
                    userAgent: navigator.userAgent,
                    platform: navigator.platform,
                    vendor: navigator.vendor,
                    language: navigator.language,
                    languages: navigator.languages ? Array.from(navigator.languages) : [],
                    hardwareConcurrency: navigator.hardwareConcurrency,
                    deviceMemory: navigator.deviceMemory,
                    maxTouchPoints: navigator.maxTouchPoints,
                    cookieEnabled: navigator.cookieEnabled,
                    doNotTrack: navigator.doNotTrack,
                    pdfViewerEnabled: navigator.pdfViewerEnabled,
                    webdriver: navigator.webdriver,
                    connection: navigator.connection ? {
                        effectiveType: navigator.connection.effectiveType,
                        rtt: navigator.connection.rtt,
                        downlink: navigator.connection.downlink,
                    } : null,
                };
            } catch (e) {
                results.navigator = { error: e.message };
            }

            // ── Screen properties ──
            try {
                results.screen = {
                    width: screen.width,
                    height: screen.height,
                    availWidth: screen.availWidth,
                    availHeight: screen.availHeight,
                    colorDepth: screen.colorDepth,
                    pixelDepth: screen.pixelDepth,
                    devicePixelRatio: window.devicePixelRatio,
                    innerWidth: window.innerWidth,
                    innerHeight: window.innerHeight,
                    outerWidth: window.outerWidth,
                    outerHeight: window.outerHeight,
                    screenX: window.screenX,
                    screenY: window.screenY,
                };
            } catch (e) {
                results.screen = { error: e.message };
            }

            // ── Timezone consistency ──
            try {
                const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
                const offset = new Date().getTimezoneOffset();
                results.timezone = {
                    timezone: tz,
                    offsetMinutes: offset,
                    dateString: new Date().toString(),
                };
            } catch (e) {
                results.timezone = { error: e.message };
            }

            // ── WebRTC leak check ──
            try {
                results.webrtc = { available: !!window.RTCPeerConnection };
            } catch (e) {
                results.webrtc = { error: e.message };
            }

            // ── Permissions API ──
            try {
                results.permissions = { available: !!navigator.permissions };
            } catch (e) {
                results.permissions = { error: e.message };
            }

            // ── Automation detection markers ──
            try {
                results.automationMarkers = {
                    webdriver: navigator.webdriver,
                    __selenium: !!window.__selenium_unwrapped,
                    __webdriver_evaluate: !!window.__webdriver_evaluate,
                    __driver_evaluate: !!window.__driver_evaluate,
                    domAutomation: !!window.domAutomation,
                    domAutomationController: !!window.domAutomationController,
                    _phantom: !!window._phantom,
                    callPhantom: !!window.callPhantom,
                    chrome_runtime: !!(window.chrome && window.chrome.runtime && window.chrome.runtime.id),
                    cdc_markers: (() => {
                        const found = [];
                        for (const key of Object.keys(document)) {
                            if (key.startsWith('$cdc_') || key.startsWith('__cdc_')) found.push(key);
                        }
                        for (const key of Object.keys(window)) {
                            if (key.startsWith('$cdc_') || key.startsWith('__cdc_')) found.push(key);
                        }
                        return found;
                    })()
                };
            } catch (e) {
                results.automationMarkers = { error: e.message };
            }

            // ── Font detection ──
            try {
                const baseFonts = ['monospace', 'sans-serif', 'serif'];
                const testFonts = ['Arial', 'Helvetica', 'Times New Roman', 'Courier New', 'Georgia', 'Verdana', 'Comic Sans MS'];
                const testString = 'mmmmmmmmmmlli';
                const testSize = '72px';
                const s = document.createElement('span');
                s.style.fontSize = testSize;
                s.innerHTML = testString;
                document.body.appendChild(s);

                const baseWidths = {};
                for (const base of baseFonts) {
                    s.style.fontFamily = base;
                    baseWidths[base] = s.offsetWidth;
                }

                const detectedFonts = [];
                for (const font of testFonts) {
                    let detected = false;
                    for (const base of baseFonts) {
                        s.style.fontFamily = `'${font}', ${base}`;
                        if (s.offsetWidth !== baseWidths[base]) {
                            detected = true;
                            break;
                        }
                    }
                    if (detected) detectedFonts.push(font);
                }
                document.body.removeChild(s);
                results.fonts = { detected: detectedFonts };
            } catch (e) {
                results.fonts = { error: e.message };
            }

            return results;
        }""")

        print("\n--- FINGERPRINT CONSISTENCY TEST RESULTS ---")
        for key, value in consistency_results.items():
            print(f"\n  [{key.upper()}]:")
            if isinstance(value, dict):
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"    {value}")
        print("--- END CONSISTENCY TESTS ---\n")

        # ── 7. Take a screenshot for reference ──
        print("\n[7] Taking screenshot ...")
        screenshot_path = "/Users/longvo/Desktop/Foxyz/pixelscan_result.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"    Screenshot saved to: {screenshot_path}")

        # ── 8. Try scrolling down and extracting more data ──
        print("\n[8] Scrolling down for additional content ...")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(3)

        extra_text = page.evaluate("""() => {
            // Get all text from elements that might have loaded after scroll
            const els = document.querySelectorAll('[class*="card"], [class*="Card"], [class*="panel"], [class*="Panel"], [class*="section"], [class*="Section"], [class*="check"], [class*="Check"], [class*="test"], [class*="Test"]');
            return Array.from(els).map(e => ({
                className: e.className?.toString()?.substring(0, 150),
                text: e.innerText?.trim()?.substring(0, 500)
            })).filter(e => e.text && e.text.length > 5);
        }""")

        if extra_text:
            print(f"\n--- ADDITIONAL CARD/SECTION DATA ({len(extra_text)} elements) ---")
            for i, item in enumerate(extra_text[:50]):  # Limit output
                print(f"\n  [{i+1}] class: {item['className']}")
                print(f"      text: {item['text'][:300]}")
            print("--- END ADDITIONAL DATA ---\n")

        # ── 9. Final summary ──
        print("\n" + "=" * 80)
        print("AUDIT COMPLETE")
        print("=" * 80)

        # Check for specific masking indicators
        full_text_lower = full_text.lower() if full_text else ""
        masking_keywords = ["masking detected", "inconsistent", "mismatch", "spoofed", "bot detected", "threat"]
        clean_keywords = ["no masking", "consistent", "human", "no threat"]

        print("\nMASKING INDICATORS FOUND:")
        for kw in masking_keywords:
            if kw in full_text_lower:
                # Find the surrounding context
                idx = full_text_lower.index(kw)
                context = full_text[max(0, idx-80):idx+len(kw)+80]
                print(f"  [!] '{kw}' -> ...{context}...")

        print("\nCLEAN INDICATORS FOUND:")
        for kw in clean_keywords:
            if kw in full_text_lower:
                idx = full_text_lower.index(kw)
                context = full_text[max(0, idx-80):idx+len(kw)+80]
                print(f"  [+] '{kw}' -> ...{context}...")

        page.close()
        context.close()


if __name__ == "__main__":
    run_audit()
