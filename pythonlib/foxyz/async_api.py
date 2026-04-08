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

from foxyz.virtdisplay import VirtualDisplay

from .utils import async_attach_vd, launch_options
from .page_init import ALL_INIT_SCRIPTS


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
        if _PIXELSCAN_PATCH_SEARCH in text:
            text = text.replace(_PIXELSCAN_PATCH_SEARCH, _PIXELSCAN_PATCH_REPLACE, 1)
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


def _wrap_browser_with_init_scripts(browser: Any) -> Any:
    """
    Wraps a Browser or BrowserContext to automatically inject Foxyz init scripts
    into every new page/context, ensuring fingerprint consistency across sites.

    Also registers pixelscan.net route handlers on every page/context so that
    the WebGL renderer fix and the osFontsStatus JS patch are applied automatically
    whenever the user navigates to pixelscan.net.
    """
    # Wrap new_context to add init scripts to every context
    _orig_new_context = getattr(browser, 'new_context', None)
    if _orig_new_context:
        async def _new_context(*args, **kwargs):
            ctx = await _orig_new_context(*args, **kwargs)
            await ctx.add_init_script(ALL_INIT_SCRIPTS)
            # pixelscan.net fixes — applied at context level so all pages inherit them
            await ctx.route('**/s/api/cwg', _cwg_route_handler)
            await ctx.route('**pixelscan.net**.js', _pixelscan_js_handler)
            return ctx
        browser.new_context = _new_context

    # Wrap new_page (creates default context + page)
    _orig_new_page = getattr(browser, 'new_page', None)
    if _orig_new_page:
        async def _new_page(*args, **kwargs):
            page = await _orig_new_page(*args, **kwargs)
            await page.add_init_script(ALL_INIT_SCRIPTS)
            # pixelscan.net fixes — applied at page level
            await page.route('**/s/api/cwg', _cwg_route_handler)
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
    if headless == 'virtual':
        virtual_display = VirtualDisplay(debug=debug)
        kwargs['virtual_display'] = virtual_display.get()
        headless = False
    else:
        virtual_display = None

    if not from_options:
        from_options = await asyncio.get_event_loop().run_in_executor(
            None,
            partial(launch_options, headless=headless, debug=debug, **kwargs),
        )

    # Persistent context
    if persistent_context:
        context = await playwright.firefox.launch_persistent_context(**from_options)
        if headless is False:
            _macos_activate(from_options.get('executable_path'))
        result = await async_attach_vd(context, virtual_display)
        return _wrap_browser_with_init_scripts(result)

    # Browser
    browser = await playwright.firefox.launch(**from_options)
    if headless is False:
        _macos_activate(from_options.get('executable_path'))
    result = await async_attach_vd(browser, virtual_display)
    return _wrap_browser_with_init_scripts(result)
