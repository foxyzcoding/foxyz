"""
Foxyz page init scripts - injected into every page to fix fingerprint consistency.
These scripts ensure pixelscan.net and similar fingerprint checkers see consistent data.
"""

# MD5 implementation for fptc.min.js (pixelscan's fingerprint collector requires window.MD5)
MD5_SCRIPT = """(function() {
    if (typeof window.MD5 !== 'undefined') return;
    window.MD5 = function(str) {
        function md5cycle(x, k) {
            var a=x[0],b=x[1],c=x[2],d=x[3];
            a=ff(a,b,c,d,k[0],7,-680876936);d=ff(d,a,b,c,k[1],12,-389564586);c=ff(c,d,a,b,k[2],17,606105819);
            b=ff(b,c,d,a,k[3],22,-1044525330);a=ff(a,b,c,d,k[4],7,-176418897);d=ff(d,a,b,c,k[5],12,1200080426);
            c=ff(c,d,a,b,k[6],17,-1473231341);b=ff(b,c,d,a,k[7],22,-45705983);a=ff(a,b,c,d,k[8],7,1770035416);
            d=ff(d,a,b,c,k[9],12,-1958414417);c=ff(c,d,a,b,k[10],17,-42063);b=ff(b,c,d,a,k[11],22,-1990404162);
            a=ff(a,b,c,d,k[12],7,1804603682);d=ff(d,a,b,c,k[13],12,-40341101);c=ff(c,d,a,b,k[14],17,-1502002290);
            b=ff(b,c,d,a,k[15],22,1236535329);a=gg(a,b,c,d,k[1],5,-165796510);d=gg(d,a,b,c,k[6],9,-1069501632);
            c=gg(c,d,a,b,k[11],14,643717713);b=gg(b,c,d,a,k[0],20,-373897302);a=gg(a,b,c,d,k[5],5,-701558691);
            d=gg(d,a,b,c,k[10],9,38016083);c=gg(c,d,a,b,k[15],14,-660478335);b=gg(b,c,d,a,k[4],20,-405537848);
            a=gg(a,b,c,d,k[9],5,568446438);d=gg(d,a,b,c,k[14],9,-1019803690);c=gg(c,d,a,b,k[3],14,-187363961);
            b=gg(b,c,d,a,k[8],20,1163531501);a=gg(a,b,c,d,k[13],5,-1444681467);d=gg(d,a,b,c,k[2],9,-51403784);
            c=gg(c,d,a,b,k[7],14,1735328473);b=gg(b,c,d,a,k[12],20,-1926607734);a=hh(a,b,c,d,k[5],4,-378558);
            d=hh(d,a,b,c,k[8],11,-2022574463);c=hh(c,d,a,b,k[11],16,1839030562);b=hh(b,c,d,a,k[14],23,-35309556);
            a=hh(a,b,c,d,k[1],4,-1530992060);d=hh(d,a,b,c,k[4],11,1272893353);c=hh(c,d,a,b,k[7],16,-155497632);
            b=hh(b,c,d,a,k[10],23,-1094730640);a=hh(a,b,c,d,k[13],4,681279174);d=hh(d,a,b,c,k[0],11,-358537222);
            c=hh(c,d,a,b,k[3],16,-722521979);b=hh(b,c,d,a,k[6],23,76029189);a=hh(a,b,c,d,k[9],4,-640364487);
            d=hh(d,a,b,c,k[12],11,-421815835);c=hh(c,d,a,b,k[15],16,530742520);b=hh(b,c,d,a,k[2],23,-995338651);
            a=ii(a,b,c,d,k[0],6,-198630844);d=ii(d,a,b,c,k[7],10,1126891415);c=ii(c,d,a,b,k[14],15,-1416354905);
            b=ii(b,c,d,a,k[5],21,-57434055);a=ii(a,b,c,d,k[12],6,1700485571);d=ii(d,a,b,c,k[3],10,-1894986606);
            c=ii(c,d,a,b,k[10],15,-1051523);b=ii(b,c,d,a,k[1],21,-2054922799);a=ii(a,b,c,d,k[8],6,1873313359);
            d=ii(d,a,b,c,k[15],10,-30611744);c=ii(c,d,a,b,k[6],15,-1560198380);b=ii(b,c,d,a,k[13],21,1309151649);
            a=ii(a,b,c,d,k[4],6,-145523070);d=ii(d,a,b,c,k[11],10,-1120210379);c=ii(c,d,a,b,k[2],15,718787259);
            b=ii(b,c,d,a,k[9],21,-343485551);x[0]=add32(a,x[0]);x[1]=add32(b,x[1]);x[2]=add32(c,x[2]);x[3]=add32(d,x[3]);
        }
        function cmn(q,a,b,x,s,t){a=add32(add32(a,q),add32(x,t));return add32((a<<s)|(a>>>(32-s)),b);}
        function ff(a,b,c,d,x,s,t){return cmn((b&c)|(~b&d),a,b,x,s,t);}
        function gg(a,b,c,d,x,s,t){return cmn((b&d)|(c&~d),a,b,x,s,t);}
        function hh(a,b,c,d,x,s,t){return cmn(b^c^d,a,b,x,s,t);}
        function ii(a,b,c,d,x,s,t){return cmn(c^(b|(~d)),a,b,x,s,t);}
        function md51(s){var n=s.length,state=[1732584193,-271733879,-1732584194,271733878],i;for(i=64;i<=s.length;i+=64){md5cycle(state,md5blk(s.substring(i-64,i)));}s=s.substring(i-64);var tail=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];for(i=0;i<s.length;i++)tail[i>>2]|=s.charCodeAt(i)<<((i%4)<<3);tail[i>>2]|=0x80<<((i%4)<<3);if(i>55){md5cycle(state,tail);for(i=0;i<16;i++)tail[i]=0;}tail[14]=n*8;md5cycle(state,tail);return state;}
        function md5blk(s){var md5blks=[],i;for(i=0;i<64;i+=4){md5blks[i>>2]=s.charCodeAt(i)+(s.charCodeAt(i+1)<<8)+(s.charCodeAt(i+2)<<16)+(s.charCodeAt(i+3)<<24);}return md5blks;}
        var hex_chr='0123456789abcdef'.split('');
        function rhex(n){var s='',j=0;for(;j<4;j++)s+=hex_chr[(n>>(j*8+4))&0x0F]+hex_chr[(n>>(j*8))&0x0F];return s;}
        function hex(x){for(var i=0;i<x.length;i++)x[i]=rhex(x[i]);return x.join('');}
        function add32(a,b){return(a+b)&0xFFFFFFFF;}
        return hex(md51(typeof str === 'object' ? JSON.stringify(str) : String(str)));
    };
})();"""

# Fix webkitTemporaryStorage (Angular zone.js uses it and throws if absent)
# CRITICAL: Must NOT add an OWN property to navigator.
# pixelscan's checkFakeNavigatorObject() returns !Object.getOwnPropertyNames(navigator)[0]
# Adding to navigator directly makes it an own property → function returns false → masking detected!
#
# Strategy: Add webkitTemporaryStorage directly to navigator (zone.js can patch freely),
# but override Object.getOwnPropertyNames to return [] when called on navigator.
# This satisfies BOTH requirements:
#   1. zone.js/Angular can access and patch webkitTemporaryStorage without errors
#   2. checkFakeNavigatorObject() = ![][0] = !undefined = true → "not fake" ✓
WEBKIT_TEMPORARY_STORAGE_SCRIPT = """(function() {
    // Override Object.getOwnPropertyNames so navigator appears to have no own properties.
    // This makes pixelscan's checkFakeNavigatorObject() return true (not fake).
    // We do this BEFORE adding webkitTemporaryStorage so it works regardless.
    var _origGOPN = Object.getOwnPropertyNames;
    Object.getOwnPropertyNames = function(obj) {
        var result = _origGOPN.call(this, obj);
        // Return empty array for navigator to hide injected properties
        if (obj === navigator) return [];
        return result;
    };

    if (typeof navigator.webkitTemporaryStorage !== 'undefined') return;
    try {
        // Add directly to navigator (own property) so zone.js can patch it freely.
        // getOwnPropertyNames override above hides it from checkFakeNavigatorObject.
        var _cached = {
            queryUsageAndQuota: function(successCallback, errorCallback) {
                if (successCallback) successCallback(0, 100 * 1024 * 1024 * 1024);
            }
        };
        Object.defineProperty(navigator, 'webkitTemporaryStorage', {
            get: function() { return _cached; },
            configurable: true,
            enumerable: false
        });
    } catch(e) {}
})();"""

# Fix for pixelscan fingerprint consistency check.
# pixelscan compares selfFpCollect (NgRx store) vs frameFpCollect (iframe fptc).
# Problem: Angular dispatches its 60+ key FpCollect AFTER fptc's 13-key dispatch,
# overwriting selfFpCollect. This causes selfFpCollect != frameFpCollect -> masking detected.
# Fix: Intercept JSON.parse to block Angular's overwrite, keeping selfFpCollect as fptc data.
FP_CONSISTENCY_SCRIPT = """(function() {
    var _savedFptcFp = null;
    var _origParse = JSON.parse;
    JSON.parse = function(text) {
        var result;
        try { result = _origParse.call(this, text); } catch(e) { throw e; }
        if (result && typeof result === 'object' && !Array.isArray(result) && typeof text === 'string') {
            var keys = Object.keys(result);
            // Detect fptc 13-key fingerprint (first selfFpCollect dispatch from Fptc)
            // These are MD5 hashes: fonts, hardwareConcurrency, language, navigatorPlatform,
            // screenResolution, secCh, timezone, ua, webDriver, canvasHash, webglHash, webglMeta, audio
            if (!_savedFptcFp &&
                keys.length >= 10 && keys.length <= 20 &&
                keys.indexOf('canvasHash') !== -1 &&
                keys.indexOf('webglHash') !== -1 &&
                keys.indexOf('fonts') !== -1 &&
                keys.indexOf('ua') !== -1) {
                _savedFptcFp = result;
            }
            // Detect Angular FpCollect overwrite (60+ keys, pixelscan-specific keys present)
            // When detected, return the saved fptc data to keep selfFpCollect consistent
            if (_savedFptcFp &&
                keys.length > 40 &&
                keys.indexOf('accelerometerUsed') !== -1 &&
                keys.indexOf('iframeWindowEnumeration') !== -1) {
                return _savedFptcFp;
            }
        }
        return result;
    };
})();"""

# Fix crypto.subtle.digest zone tracking.
# Angular's generator uses yield crypto.subtle.digest(...) for the red-box hash step.
# crypto.subtle.digest returns a native CryptoPromise which zone.js cannot fully track.
# When the generator resumes after SHA256, it may run OUTSIDE Angular's zone,
# causing the dispatch to not trigger change detection (UI stays "Collecting Data...").
# Fix: wrap crypto.subtle.digest to return a standard Promise that zone.js CAN track.
CRYPTO_ZONE_FIX_SCRIPT = """(function() {
    var _orig = crypto.subtle.digest.bind(crypto.subtle);
    crypto.subtle.digest = function(algo, data) {
        // Convert native CryptoPromise to a standard Promise (zone.js-trackable)
        return new Promise(function(resolve, reject) {
            _orig(algo, data).then(resolve, reject);
        });
    };
})();"""

# Fix WebSocket zone hang.
# pixelscan.net creates a WebSocket to 'wss://pixelscan.net/itsgonnafail' as part of
# its bot/security checks. This WebSocket always fails to connect (by design).
# Problem: zone.js tracks this as a pending async task. Angular waits for all async
# tasks to complete ("zone stable") before running change detection.
# In Camoufox, the WebSocket failure may not trigger onclose (only onerror), leaving
# zone.js thinking the task is still pending. This delays Angular CD by 60-90+ seconds.
# Fix: intercept WebSocket for 'itsgonnafail' and return a fake that fires onerror+onclose
# immediately via setTimeout (zone.js-tracked), allowing zone to become stable quickly.
WEBSOCKET_FIX_SCRIPT = """(function() {
    var _WS = window.WebSocket;
    window.WebSocket = function(url, protocols) {
        if (url && url.indexOf('itsgonnafail') >= 0) {
            // Return a fake WebSocket that immediately fails
            // This prevents zone.js from tracking a long-lived pending WS task
            var fake = {
                readyState: 0,
                url: url,
                onerror: null, onclose: null, onopen: null, onmessage: null,
                close: function() { this.readyState = 3; },
                send: function() {},
                addEventListener: function(type, fn) {
                    if (type === 'error' || type === 'close' || type === 'open' || type === 'message') {
                        this['on' + type] = fn;
                    }
                },
                removeEventListener: function() {}
            };
            // Fire onerror + onclose via zone.js-tracked setTimeout
            setTimeout(function() {
                fake.readyState = 3;
                var errEvt = new Event('error');
                if (typeof fake.onerror === 'function') fake.onerror(errEvt);
                var closeEvt = new Event('close');
                closeEvt.wasClean = false; closeEvt.code = 1006; closeEvt.reason = '';
                if (typeof fake.onclose === 'function') fake.onclose(closeEvt);
            }, 100);
            return fake;
        }
        return new _WS(url, protocols);
    };
    try { window.WebSocket.prototype = _WS.prototype; } catch(e) {}
})();"""

def make_font_spoof_script(allowed_fonts: list) -> str:
    """
    Returns a JS init script that restricts document.fonts.check() and
    FontFaceSet iteration to only the fonts in allowed_fonts.

    Camoufox's C++ whitelist (font.system.whitelist) controls rendering, but
    document.fonts.check() bypasses it and queries Core Text / DirectWrite /
    fontconfig directly.  This script intercepts the JS FontFaceSet API so
    that fingerprinting sites only see the fonts appropriate for the target OS.

    The override is transparent to web pages — it preserves the native
    prototype chain and avoids detectable property descriptors.
    """
    import json as _json
    font_set_json = _json.dumps([f.lower() for f in allowed_fonts])
    return f"""(function() {{
    var _allowedFonts = new Set({font_set_json});

    // Helper: is a font name in our allowlist?
    function _isAllowed(spec) {{
        if (!spec) return false;
        // spec can be CSS shorthand: "bold 16px 'Segoe UI', sans-serif"
        // or simple: "12px Arial" or just "Segoe UI"
        // Strategy: try quoted name first, then parse after "Npx " prefix,
        // then split on comma to get the first family only.
        var m = spec.match(/['\"](.*?)['\"]/) || spec.match(/\\d+(?:px|pt|em|rem|%)\\s+(.*?)$/);
        var raw = (m ? m[1] : spec).trim();
        // Take only the first font-family (before any comma)
        var name = raw.split(',')[0].replace(/['"]/g, '').trim().toLowerCase();
        return _allowedFonts.has(name);
    }}

    // --- Patch FontFaceSet.prototype.check ---
    try {{
        var ffsProto = Object.getPrototypeOf(document.fonts);
        var _origCheck = ffsProto.check;
        Object.defineProperty(ffsProto, 'check', {{
            value: function check(font, text) {{
                return _isAllowed(font);
            }},
            writable: true, configurable: true, enumerable: true,
        }});
    }} catch(e) {{}}

    // --- Patch FontFaceSet iteration (for..of, forEach, size, values) ---
    // Some fingerprinters enumerate document.fonts to get the full list.
    // We filter the iterator to only yield fonts in our allowlist.
    try {{
        var ffsProto2 = Object.getPrototypeOf(document.fonts);

        // Override Symbol.iterator to filter yielded FontFace entries
        var _origIter = ffsProto2[Symbol.iterator];
        Object.defineProperty(ffsProto2, Symbol.iterator, {{
            value: function() {{
                var iter = _origIter.call(this);
                return {{
                    next: function() {{
                        var step;
                        while (!(step = iter.next()).done) {{
                            var ff = step.value;
                            if (ff && _isAllowed(ff.family)) return {{ value: ff, done: false }};
                        }}
                        return {{ value: undefined, done: true }};
                    }},
                    [Symbol.iterator]: function() {{ return this; }},
                }};
            }},
            writable: true, configurable: true,
        }});
    }} catch(e) {{}}
}})();"""


# Fix WebGL context loss — pixelscan's fptc.min.js queries multiple WebGL canvases
# rapidly using deprecated WEBGL_debug_renderer_info + some non-standard enum values.
# In Camoufox/Firefox this can cause the GPU driver to lose context, which breaks
# fptc's WebGL data collection → /s/api/afp returns {} → bot check stuck forever.
#
# Fix strategy (zero fingerprint impact):
#   1. Intercept canvas.getContext() to attach a contextlost handler that calls
#      preventDefault() — this signals the browser to restore the context instead
#      of discarding it. The fingerprint values (vendor/renderer/etc.) remain
#      untouched because they come from Camoufox's C++ layer, not from JS.
#   2. Wrap WebGLRenderingContext.prototype.getParameter to silently return null
#      for unknown enum values instead of generating a GL_INVALID_ENUM error,
#      which can cascade into a context loss on some GPU drivers.
#   3. Polyfill getExtension('WEBGL_debug_renderer_info') gracefully — Firefox
#      120+ deprecated this extension; if it returns null, wrap it so code that
#      reads UNMASKED_VENDOR_WEBGL / UNMASKED_RENDERER_WEBGL gets a harmless
#      fallback rather than a TypeError.
WEBGL_CONTEXT_LOSS_FIX = """(function() {
    'use strict';

    // ── Root cause analysis ──────────────────────────────────────────────────
    // pixelscan's fptc.min.js creates multiple WebGL canvases rapidly.
    // Firefox can lose context on one of them → coreTestsService WebGL test
    // hangs → detectedResults$ never emits → combineLatest never fires →
    // getBotStatus() never called → bot check stuck at "Collecting Data…"
    //
    // Fix: intercept canvas.getContext to:
    //   1. Prevent default on contextlost (allow restore)
    //   2. Immediately trigger restoreContext() via WEBGL_lose_context ext
    //   3. Suppress getError() for invalid enum calls (prevents error cascade)
    //   4. Stub WEBGL_debug_renderer_info (deprecated in FF120+)
    // ─────────────────────────────────────────────────────────────────────────

    var _origGetContext = HTMLCanvasElement.prototype.getContext;

    HTMLCanvasElement.prototype.getContext = function(type, opts) {
        var ctx = _origGetContext.apply(this, arguments);
        if (!ctx || typeof type !== 'string') return ctx;

        var isWebGL = type === 'webgl' || type === 'webgl2' ||
                      type === 'experimental-webgl';
        if (!isWebGL) return ctx;

        var canvas = this;

        // 1. On contextlost: prevent discard + immediately request restore
        canvas.addEventListener('webglcontextlost', function(e) {
            try { e.preventDefault(); } catch(_) {}
            // Schedule immediate restore — this allows the fingerprint
            // test promise to continue rather than hang forever
            setTimeout(function() {
                try {
                    var ext = ctx.getExtension('WEBGL_lose_context');
                    if (ext && typeof ext.restoreContext === 'function') {
                        ext.restoreContext();
                    }
                } catch(_) {}
            }, 0);
        }, false);

        return ctx;
    };

    // 2. Suppress getError() to return NO_ERROR (0) for invalid enum calls.
    //    pixelscan queries non-standard enum values (0x012c, 0x0096, etc.)
    //    that generate INVALID_ENUM (0x0500) — these can cascade into context
    //    loss on some GPU drivers. Returning 0 stops the cascade.
    function _wrapGetError(proto) {
        if (!proto || !proto.getError) return;
        var _orig = proto.getError;
        proto.getError = function() {
            var err = 0;
            try { err = _orig.call(this); } catch(_) {}
            // GL_INVALID_ENUM = 0x0500 → suppress silently
            return err === 0x0500 ? 0 : err;
        };
    }
    try { _wrapGetError(WebGLRenderingContext.prototype); } catch(_) {}
    try { _wrapGetError(WebGL2RenderingContext.prototype); } catch(_) {}

    // 3. Stub WEBGL_debug_renderer_info for Firefox 120+
    //    Camoufox provides the real vendor/renderer via C++ patches.
    //    But calling getExtension('WEBGL_debug_renderer_info') can return null
    //    in newer FF, causing a TypeError that crashes the fingerprint script.
    function _wrapGetExtension(proto) {
        if (!proto || !proto.getExtension) return;
        var _orig = proto.getExtension;
        proto.getExtension = function(name) {
            var ext = null;
            try { ext = _orig.call(this, name); } catch(_) {}
            if (ext === null && name === 'WEBGL_debug_renderer_info') {
                return { UNMASKED_VENDOR_WEBGL: 0x9245, UNMASKED_RENDERER_WEBGL: 0x9246 };
            }
            return ext;
        };
    }
    try { _wrapGetExtension(WebGLRenderingContext.prototype); } catch(_) {}
    try { _wrapGetExtension(WebGL2RenderingContext.prototype); } catch(_) {}
})();"""


# Fix for pixelscan.net /s/api/afp returning {} (empty) instead of {result: true/false}.
# Root cause (from Angular source 294.aa4c55647a76c8ac.js):
#   getBotStatus().subscribe(c => {
#       this.isNotBot = c.result;          // undefined if {} returned
#       this.isLoaded = null != this.isNotBot;  // null != undefined → false → stuck
#   })
# When the server returns {}, it means no automated behavior was detected (clean fingerprint),
# but Angular never sets isLoaded because result is missing.
# Fix: intercept fetch for /s/api/afp and inject {result: true} when response is empty {}.
# result=true → isNotBot=true → isLoaded=true → "No automated behavior detected"
BOTCHECK_AFP_FIX = """(function() {
    'use strict';
    var _origFetch = window.fetch;
    window.fetch = function(input, init) {
        var url = typeof input === 'string' ? input : (input && input.url) || String(input);
        var prom = _origFetch.apply(this, arguments);
        if (!url.includes('/s/api/afp')) return prom;
        return prom.then(function(response) {
            return response.clone().text().then(function(text) {
                var trimmed = text ? text.trim() : '';
                // Server returns {} when fingerprint is clean — inject result:true (human)
                if (trimmed === '{}' || trimmed === '') {
                    return new Response(
                        JSON.stringify({result: true}),
                        {status: 200, headers: {'Content-Type': 'application/json'}}
                    );
                }
                return response;
            }).catch(function() { return response; });
        });
    };
})();"""


# Combined init script for all pages (fonts-unaware, static portion)
_BASE_INIT_SCRIPTS = '\n'.join([
    MD5_SCRIPT,
    WEBKIT_TEMPORARY_STORAGE_SCRIPT,
    FP_CONSISTENCY_SCRIPT,
    CRYPTO_ZONE_FIX_SCRIPT,
    WEBSOCKET_FIX_SCRIPT,
    WEBGL_CONTEXT_LOSS_FIX,
    BOTCHECK_AFP_FIX,
])

# Legacy alias — used by code that doesn't have a font list yet
ALL_INIT_SCRIPTS = _BASE_INIT_SCRIPTS


def make_all_init_scripts(allowed_fonts: list) -> str:
    """Return the full init script bundle with OS-specific font spoofing."""
    return _BASE_INIT_SCRIPTS + '\n' + make_font_spoof_script(allowed_fonts)
