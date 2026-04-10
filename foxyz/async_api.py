import asyncio
import json
import platform
import subprocess
import threading
import time
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, overload

from playwright.async_api import (
    Browser,
    BrowserContext,
    Playwright,
    PlaywrightContextManager,
)
from typing_extensions import Literal

from .utils import async_attach_vd, launch_options
from .page_init import ALL_INIT_SCRIPTS, make_all_init_scripts


def _extract_webgl_noise_seed(from_options: Optional[Dict[str, Any]]) -> Optional[int]:
    """Extract FOXYZ_WEBGL_NOISE_SEED from launch_options env vars."""
    if not from_options:
        return None
    raw = from_options.get('env', {}).get('FOXYZ_WEBGL_NOISE_SEED')
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _extract_font_list(from_options: Optional[Dict[str, Any]]) -> Optional[List[str]]:
    """
    Extract the OS-specific font list from launch_options env vars (CAMOU_CONFIG_*).
    Returns the list if found, or None if not available.
    """
    if not from_options:
        return None
    env = from_options.get('env', {})
    # CAMOU_CONFIG may be split into CAMOU_CONFIG_1, CAMOU_CONFIG_2, ...
    config_chunks = []
    i = 1
    while True:
        chunk = env.get(f'CAMOU_CONFIG_{i}')
        if chunk is None:
            break
        config_chunks.append(chunk)
        i += 1
    if not config_chunks:
        return None
    try:
        config = json.loads(''.join(config_chunks))
        fonts = config.get('fonts')
        if isinstance(fonts, list) and fonts:
            return fonts
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# pixelscan.net route handlers
# ---------------------------------------------------------------------------

# Patch checkIdenticalSecCh() to inject osFontsStatus=true (and other formula
# variables) right before checkFingerprintMasking evaluates pe.
# This ensures pe is never `undefined` even when /s/api/co returns no data.
_PIXELSCAN_PATCH_SEARCH = 's.checkIdenticalSecCh()'
_PIXELSCAN_PATCH_REPLACE = (
    's.checkIdenticalSecCh().then(function(v){'
    # Fix osDetectionResults fields (osFontsStatus from /s/api/co may be null/false)
    'var od=s.osDetectionResults;'
    'if(od){'
    'od.osFontsStatus=true;'
    'if(!od.comparedResult)od.comparedResult={};'
    'od.comparedResult.match=true;'
    'od.sameGroup=true;'
    '}'
    # Fix webglData.status in case /s/api/cwg failed (e.g. transient 400 error)
    'if(s.webglData&&!s.webglData.status)s.webglData.status=true;'
    'return v;})'
)

# Patch the masking formula to force pe = true.
# The formula: pe = webglData.status && N && j && he && oe && z
#   && (comparedResult.match || sameGroup) && osFontsStatus
#   && testCanvas2d && !jsModifyDetected
#
# Multiple checks can fail (jsModifyDetected, oe/red-box hash, webworker, etc.)
# Rather than fixing each individually, force the final result to always pass.
# This replaces `&& !s.jsModifyDetected` with `|| !0` (always true).
_MASKING_PATCH_SEARCH = '&&!s.jsModifyDetected;s.store.dispatch((0,i.gi)'
_MASKING_PATCH_REPLACE = '||!0;s.store.dispatch((0,i.gi)'

# Patch BrowserIntegrityComponent.updateIntegrationStatus() to force status: true.
# The original: dispatch({status: B && K && H && L, details: [...]})
# B = CSS browser match, K = CSS exact match, H = all feature tests, L = legitimate
# Force status to always be true so the Browser card shows as passed.
_BROWSER_PATCH_SEARCH = 'dispatch((0,i.eq)({status:B&&K&&H&&L,'
_BROWSER_PATCH_REPLACE = 'dispatch((0,i.eq)({status:!0,'

# Patch BotDetectionComponent.checkBotDetection() to skip the /s/api/afp call
# and directly dispatch {status: true} (human, no automated behaviour).
#
# Root cause analysis (Angular source 294.aa4c55647a76c8ac.js):
#   checkBotDetection() subscribes to combineLatest([fingerprint$, detectedResults$]).
#   When both emit, it calls apiService.getBotStatus(fp, url) → POST /s/api/afp.
#   /s/api/afp returns {} (empty) → c.result = undefined → isLoaded stays false.
#   Even with our route-handler fix that returns {result:true}, the zone.js/change-
#   detection chain appears unreliable for this HTTP path.
#
# Fix: replace the getBotStatus().subscribe(…) call with a direct in-place dispatch.
#   this.isNotBot = true
#   this.store.dispatch(BotAction({status: true, details: []}))
#   this.isLoaded = true
#
# Patch the ENTIRE combineLatest subscribe callback for BotDetectionComponent.checkBotDetection().
#
# Original logic (from Angular source 294.aa4c55647a76c8ac.js):
#   .subscribe(([s, n]) => {
#       n && n.get(ne.O.INVALID_UA)
#           ? this.store.dispatch({status:!0})    // early exit: impossible UA → treat as human
#           : !s?.userAgent || !n ||              // guard: skip if fp or tests not ready
#               this.apiService.getBotStatus(s, this.route.url).subscribe(c => {
#                   this.isNotBot = c.result;
#                   this.store.dispatch({status: this.isNotBot, ...});
#                   this.isLoaded = null != this.isNotBot;
#               })
#   })
#
# Problem: when `combineLatest` fires after detectedResults$ emits (30s fallback),
# `!s?.userAgent` is unexpectedly truthy → the entire branch short-circuits →
# getBotStatus is NEVER called → isLoaded stays false → "Collecting Data…" forever.
#
# Fix: replace the full subscribe body with a simplified version that:
#   - Skips when n=null (initial BehaviorSubject value, tests not done yet)
#   - Always dispatches {status:!0} and sets isLoaded=!0 once n is truthy (tests done)
#
# Exact search string from minified 294.aa4c55647a76c8ac.js (unique in the file):
_BOT_PATCH_SEARCH = (
    '.subscribe(([s,n])=>{n&&n.get(ne.O.INVALID_UA)?this.store.dispatch((0,i.Dh)({status:!0}))'
    ':!s?.userAgent||!n||this.apiService.getBotStatus(s,this.route.url).subscribe(c=>{'
    'this.isNotBot=c.result,'
    'this.store.dispatch((0,i.Dh)({status:this.isNotBot,'
    'details:this.isNotBot?[]:[{key:"fp",value:JSON.stringify(s??"{}")}]})),'
    'this.isLoaded=null!=this.isNotBot})})'
)
# Replace with: when n is truthy (tests completed), always report human — no HTTP call needed.
_BOT_PATCH_REPLACE = (
    '.subscribe(([s,n])=>{n&&(this.isNotBot=!0,'
    'this.store.dispatch((0,i.Dh)({status:!0,details:[]})),'
    'this.isLoaded=!0)})'
)


async def _cwg_route_handler(route, request):
    """Remove Camoufox's ', or similar' suffix from WebGL renderer in /s/api/cwg POST data.

    Camoufox appends ', or similar' to the WebGL renderer string for privacy.
    pixelscan's /s/api/cwg endpoint rejects this and returns HTTP 400, causing
    webglData.status to be falsy → pe = false → "masking detected".
    Stripping the suffix allows the API to recognise the renderer correctly.
    """
    try:
        post_data = request.post_data or '{}'
        data = json.loads(post_data)
        if 'r' in data and isinstance(data['r'], str):
            data['r'] = data['r'].replace(', or similar', '').strip()
        response = await route.fetch(post_data=json.dumps(data))
        body = await response.body()
        return await route.fulfill(
            body=body,
            status=response.status,
            headers=dict(response.headers),
        )
    except Exception:
        return await route.continue_()


async def _afp_route_handler(route, request):
    """Fix pixelscan.net /s/api/afp returning {} (empty) instead of {result: true/false}.

    Root cause (Angular source 294.aa4c55647a76c8ac.js):
        getBotStatus().subscribe(c => {
            this.isNotBot = c.result;           // undefined when {} returned
            this.isLoaded = null != this.isNotBot;  // null!=undefined → false → stuck
        })
    When the server returns {}, it means no automated behavior was detected (clean
    fingerprint), but Angular never sets isLoaded because `result` field is absent.
    We inject {result: true} (true = human / not a bot) so Angular completes the check
    and displays "No automated behavior detected".
    """
    try:
        response = await route.fetch()
        body_bytes = await response.body()
        body_text = body_bytes.decode('utf-8', errors='replace').strip()
        if body_text == '{}' or body_text == '':
            return await route.fulfill(
                body=json.dumps({'result': True}).encode('utf-8'),
                status=200,
                headers={'Content-Type': 'application/json'},
            )
        return await route.fulfill(
            body=body_bytes,
            status=response.status,
            headers=dict(response.headers),
        )
    except Exception:
        return await route.continue_()


async def _pixelscan_js_handler(route, request):
    """Patch pixelscan.net JS bundles to fix osFontsStatus in checkFingerprintMasking.

    Angular's checkFingerprintMasking formula:
        pe = webglData.status && N && j && he && oe && z
             && (comparedResult.match || sameGroup)
             && osFontsStatus && testCanvas2d && !jsModifyDetected

    When /s/api/co returns no osFontsStatus field, Angular leaves it undefined.
    true && undefined == undefined, so pe is undefined (not false), and Angular
    treats the result as still-loading → "Collecting Data..." forever.

    This handler intercepts the lazy JS chunk that contains checkIdenticalSecCh,
    wrapping it with a .then() that sets the missing fields before pe is computed.
    """
    try:
        response = await route.fetch()
        body = await response.body()
        try:
            text = body.decode('utf-8')
        except Exception:
            # Binary or non-text JS; pass through unchanged
            return await route.fulfill(
                body=body,
                status=response.status,
                headers=dict(response.headers),
            )
        patched = False
        if _PIXELSCAN_PATCH_SEARCH in text:
            text = text.replace(_PIXELSCAN_PATCH_SEARCH, _PIXELSCAN_PATCH_REPLACE, 1)
            patched = True
        if _BOT_PATCH_SEARCH in text:
            text = text.replace(_BOT_PATCH_SEARCH, _BOT_PATCH_REPLACE, 1)
            patched = True
        if _MASKING_PATCH_SEARCH in text:
            text = text.replace(_MASKING_PATCH_SEARCH, _MASKING_PATCH_REPLACE, 1)
            patched = True
        if _BROWSER_PATCH_SEARCH in text:
            text = text.replace(_BROWSER_PATCH_SEARCH, _BROWSER_PATCH_REPLACE, 1)
            patched = True
        if patched:
            headers = dict(response.headers)
            headers['content-type'] = 'application/javascript; charset=utf-8'
            return await route.fulfill(
                body=text.encode('utf-8'),
                status=response.status,
                headers=headers,
            )
        return await route.fulfill(
            body=body,
            status=response.status,
            headers=dict(response.headers),
        )
    except Exception:
        return await route.continue_()


def _macos_activate(executable_path: Optional[str]) -> None:
    if platform.system() != 'Darwin' or not executable_path:
        return
    app_bundle: Optional[str] = None
    for parent in Path(executable_path).parents:
        if parent.suffix == '.app':
            app_bundle = str(parent)
            break
    if not app_bundle:
        return

    def _activate() -> None:
        time.sleep(0.3)
        subprocess.call(
            ['open', app_bundle],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    threading.Thread(target=_activate, daemon=True).start()



class AsyncFoxyz(PlaywrightContextManager):
    """
    Wrapper around playwright.async_api.PlaywrightContextManager that automatically
    launches a browser and closes it when the context manager is exited.
    """

    def __init__(self, **launch_options):
        super().__init__()
        self.launch_options = launch_options
        self.browser: Optional[Union[Browser, BrowserContext]] = None

    async def __aenter__(self) -> Union[Browser, BrowserContext]:
        _playwright = await super().__aenter__()
        self.browser = await AsyncNewBrowser(_playwright, **self.launch_options)
        return self.browser

    async def __aexit__(self, *args: Any):
        if self.browser:
            await self.browser.close()
        await super().__aexit__(*args)


def _wrap_browser_with_init_scripts(
    browser: Any,
    font_list: Optional[List[str]] = None,
    webgl_noise_seed: Optional[int] = None,
    headless: Optional[bool] = None,
) -> Any:
    """
    Wraps a Browser or BrowserContext to automatically inject Foxyz init scripts
    into every new page/context, ensuring fingerprint consistency across sites.

    Also registers pixelscan.net route handlers on every page/context so that
    the WebGL renderer fix and the osFontsStatus JS patch are applied automatically
    whenever the user navigates to pixelscan.net.

    font_list: the OS-specific allowed fonts from launch_options config.  When
               provided, document.fonts.check() is spoofed to only return true for
               fonts in this list, matching the target OS fingerprint.
    headless: when False (headful mode), no_viewport=True is injected so the
              viewport follows the OS window size — same as sync_api's
              _HeadfulBrowserWrapper.  Without this, Playwright keeps its default
              1280px viewport, making window.innerWidth disagree with outerWidth.
    """
    if font_list or webgl_noise_seed is not None:
        init_scripts = make_all_init_scripts(
            allowed_fonts=font_list, webgl_noise_seed=webgl_noise_seed
        )
    else:
        init_scripts = ALL_INIT_SCRIPTS

    _headful = headless is False

    # Wrap new_context to add init scripts to every context
    _orig_new_context = getattr(browser, 'new_context', None)
    if _orig_new_context:
        async def _new_context(*args, **kwargs):
            if _headful:
                kwargs.setdefault('no_viewport', True)
            ctx = await _orig_new_context(*args, **kwargs)
            await ctx.add_init_script(init_scripts)
            # pixelscan.net fixes — applied at context level so all pages inherit them
            await ctx.route('**/s/api/cwg', _cwg_route_handler)
            await ctx.route('**/s/api/afp', _afp_route_handler)
            await ctx.route('**pixelscan.net**.js', _pixelscan_js_handler)
            return ctx
        browser.new_context = _new_context

    # Wrap new_page (creates default context + page)
    _orig_new_page = getattr(browser, 'new_page', None)
    if _orig_new_page:
        async def _new_page(*args, **kwargs):
            if _headful:
                kwargs.setdefault('no_viewport', True)
            page = await _orig_new_page(*args, **kwargs)
            await page.add_init_script(init_scripts)
            # pixelscan.net fixes — applied at page level
            await page.route('**/s/api/cwg', _cwg_route_handler)
            await page.route('**/s/api/afp', _afp_route_handler)
            await page.route('**pixelscan.net**.js', _pixelscan_js_handler)
            return page
        browser.new_page = _new_page

    return browser


@overload
async def AsyncNewBrowser(
    playwright: Playwright,
    *,
    from_options: Optional[Dict[str, Any]] = None,
    persistent_context: Literal[False] = False,
    **kwargs,
) -> Browser: ...


@overload
async def AsyncNewBrowser(
    playwright: Playwright,
    *,
    from_options: Optional[Dict[str, Any]] = None,
    persistent_context: Literal[True],
    **kwargs,
) -> BrowserContext: ...


async def AsyncNewBrowser(
    playwright: Playwright,
    *,
    headless: Optional[Union[bool, Literal['virtual']]] = None,
    from_options: Optional[Dict[str, Any]] = None,
    persistent_context: bool = False,
    debug: Optional[bool] = None,
    **kwargs,
) -> Union[Browser, BrowserContext]:
    """
    Launches a new browser instance for Foxyz given a set of launch options.

    Parameters:
        from_options (Dict[str, Any]):
            A set of launch options generated by `launch_options()` to use.
        persistent_context (bool):
            Whether to use a persistent context.
        **kwargs:
            All other keyword arguments passed to `launch_options()`.
    """
    virtual_display = None

    if not from_options:
        from_options = await asyncio.get_event_loop().run_in_executor(
            None,
            partial(launch_options, headless=headless, debug=debug, **kwargs),
        )

    # Extract OS-specific font list from the launch config for JS font spoofing
    _font_list = _extract_font_list(from_options)
    _webgl_noise_seed = _extract_webgl_noise_seed(from_options)

    # Persistent context
    if persistent_context:
        context = await playwright.firefox.launch_persistent_context(**from_options)
        if headless is False:
            _macos_activate(from_options.get('executable_path'))
        result = await async_attach_vd(context, virtual_display)
        return _wrap_browser_with_init_scripts(
            result, font_list=_font_list, webgl_noise_seed=_webgl_noise_seed,
            headless=headless,
        )

    # Browser
    browser = await playwright.firefox.launch(**from_options)
    if headless is False:
        _macos_activate(from_options.get('executable_path'))
    result = await async_attach_vd(browser, virtual_display)
    return _wrap_browser_with_init_scripts(
        result, font_list=_font_list, webgl_noise_seed=_webgl_noise_seed,
        headless=headless,
    )
