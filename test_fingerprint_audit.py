"""
Comprehensive fingerprint audit — test Foxyz against multiple checking services.
Collects detailed results from CreepJS, BrowserLeaks, and Pixelscan.
"""
import json
import time
from foxyz import Foxyz


def wait_and_extract(page, url, wait_sec, extract_fn, label):
    """Navigate to URL, wait, then extract data."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        print(f"  Loading... ({wait_sec}s)")
        time.sleep(wait_sec)
        return extract_fn(page)
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def test_creepjs(page):
    """CreepJS — most detailed lie detection and trust scoring."""
    def extract(p):
        for i in range(20):
            time.sleep(3)
            ready = p.evaluate("""(() => {
                const el = document.querySelector('.fingerprint-header');
                return el ? el.innerText : '';
            })()""")
            if 'trust' in ready.lower() or 'fingerprint' in ready.lower():
                break
            print(f"  [{(i+1)*3}s] waiting for CreepJS...")

        data = p.evaluate("""(() => {
            const results = {};
            results.full_text = document.body.innerText.substring(0, 4000);

            // Lie detection
            const lies = [];
            const allText = document.body.innerText;
            const lieMatches = allText.match(/lie[sd]?.*?detected|tampering|fake|spoof|phantom|suspicious/gi);
            if (lieMatches) lies.push(...new Set(lieMatches));
            results.lies = lies;

            return JSON.stringify(results);
        })()""")

        parsed = json.loads(data)
        print(f"\n  --- CreepJS Results ---")
        if parsed.get('lies'):
            print(f"\n  LIES DETECTED:")
            for lie in parsed['lies'][:20]:
                print(f"    - {lie}")

        full = parsed.get('full_text', '')
        print(f"\n  Full text (first 3000 chars):")
        print(f"  {full[:3000]}")
        return parsed

    return wait_and_extract(page,
        'https://abrahamjuliot.github.io/creepjs/',
        10, extract, "CreepJS - Lie Detection & Trust Score")


def test_browserleaks_canvas(page):
    """BrowserLeaks Canvas test."""
    def extract(p):
        time.sleep(5)
        data = p.evaluate("document.body.innerText.substring(0, 2000)")
        print(f"  {data[:1500]}")
        return data

    return wait_and_extract(page,
        'https://browserleaks.com/canvas',
        5, extract, "BrowserLeaks - Canvas Fingerprint")


def test_browserleaks_webgl(page):
    """BrowserLeaks WebGL test."""
    def extract(p):
        time.sleep(5)
        data = p.evaluate("document.body.innerText.substring(0, 2000)")
        print(f"  {data[:1500]}")
        return data

    return wait_and_extract(page,
        'https://browserleaks.com/webgl',
        5, extract, "BrowserLeaks - WebGL Fingerprint")


def test_browserleaks_js(page):
    """BrowserLeaks JavaScript test — navigator properties."""
    def extract(p):
        time.sleep(5)
        data = p.evaluate("document.body.innerText.substring(0, 3000)")
        print(f"  {data[:2000]}")
        return data

    return wait_and_extract(page,
        'https://browserleaks.com/javascript',
        5, extract, "BrowserLeaks - JavaScript / Navigator")


def test_browserleaks_fonts(page):
    """BrowserLeaks Font detection."""
    def extract(p):
        time.sleep(8)
        data = p.evaluate("document.body.innerText.substring(0, 2000)")
        print(f"  {data[:1500]}")
        return data

    return wait_and_extract(page,
        'https://browserleaks.com/fonts',
        5, extract, "BrowserLeaks - Font Detection")


def test_pixelscan(page):
    """Pixelscan — final verdict check."""
    def extract(p):
        for i in range(20):
            time.sleep(3)
            state = p.evaluate("""(() => {
                const body = document.body ? document.body.innerText : '';
                const verdict = body.match(/Your Browser Fingerprint is (consistent|inconsistent)/i);
                return JSON.stringify({
                    verdict: verdict ? verdict[1] : null,
                    collecting: body.includes('Collecting Data'),
                    scanning: body.includes('is scanning'),
                });
            })()""")
            s = json.loads(state)
            elapsed = (i+1)*3

            if s.get('verdict'):
                print(f"  [{elapsed:3d}s] VERDICT: {s['verdict'].upper()}")
                details = p.evaluate("document.body.innerText.substring(0, 3000)")
                print(f"\n  {details[:2000]}")
                return {'verdict': s['verdict'], 'details': details}

            status = 'SCANNING' if s['scanning'] else ('COLLECTING' if s['collecting'] else 'WAITING')
            print(f"  [{elapsed:3d}s] {status}")

        print("  No verdict after 60s")
        return None

    return wait_and_extract(page,
        'https://pixelscan.net/fingerprint-check',
        5, extract, "Pixelscan - Final Verdict")


def test_fingerprint_com(page):
    """Fingerprint.com demo — industry standard detection."""
    def extract(p):
        time.sleep(8)
        data = p.evaluate("document.body.innerText.substring(0, 2000)")
        print(f"  {data[:1500]}")
        return data

    return wait_and_extract(page,
        'https://fingerprint.com/demo/',
        5, extract, "Fingerprint.com - Bot Detection")


def main():
    print("=" * 60)
    print("  FOXYZ FINGERPRINT COMPREHENSIVE AUDIT")
    print("=" * 60)

    with Foxyz(headless=False) as browser:
        page = browser.new_page()

        # Collect raw navigator data
        page.goto('about:blank')
        nav_data = page.evaluate("""(() => {
            return JSON.stringify({
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                languages: navigator.languages,
                hardwareConcurrency: navigator.hardwareConcurrency,
                deviceMemory: navigator.deviceMemory,
                doNotTrack: navigator.doNotTrack,
                webdriver: navigator.webdriver,
                oscpu: navigator.oscpu,
                buildID: navigator.buildID,
                devicePixelRatio: window.devicePixelRatio,
                screenWidth: screen.width,
                screenHeight: screen.height,
                availWidth: screen.availWidth,
                availHeight: screen.availHeight,
                colorDepth: screen.colorDepth,
                intlLocale: Intl.DateTimeFormat().resolvedOptions().locale,
                intlTimezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            }, null, 2);
        })()""")
        print(f"\n{'='*60}")
        print(f"  RAW NAVIGATOR DATA")
        print(f"{'='*60}")
        print(f"  {nav_data}")

        # Run all tests
        test_creepjs(page)
        test_browserleaks_canvas(page)
        test_browserleaks_webgl(page)
        test_browserleaks_js(page)
        test_browserleaks_fonts(page)
        test_pixelscan(page)
        test_fingerprint_com(page)

        print(f"\n\n{'='*60}")
        print(f"  AUDIT COMPLETE")
        print(f"{'='*60}")


if __name__ == '__main__':
    main()
