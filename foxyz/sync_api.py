import json
import platform
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, overload

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Playwright,
    PlaywrightContextManager,
)
from typing_extensions import Literal

from .exceptions import InvalidProxy
from .utils import launch_options, sync_attach_vd
from .page_init import ALL_INIT_SCRIPTS, make_all_init_scripts


def _extract_font_list(from_options: Optional[Dict[str, Any]]) -> Optional[List[str]]:
    """Extract OS-specific font list from launch_options CAMOU_CONFIG env vars."""
    if not from_options:
        return None
    env = from_options.get('env', {})
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


# ---------------------------------------------------------------------------
# pixelscan.net route handlers (sync versions)
# ---------------------------------------------------------------------------

# Import patch strings from async_api to stay in sync
from .async_api import (
    _PIXELSCAN_PATCH_SEARCH,
    _PIXELSCAN_PATCH_REPLACE,
    _BOT_PATCH_SEARCH,
    _BOT_PATCH_REPLACE,
    _MASKING_PATCH_SEARCH,
    _MASKING_PATCH_REPLACE,
    _BROWSER_PATCH_SEARCH,
    _BROWSER_PATCH_REPLACE,
)


def _sync_cwg_route_handler(route):
    """Sync version: strip ', or similar' from WebGL renderer in /s/api/cwg POST."""
    try:
        request = route.request
        post_data = request.post_data or '{}'
        data = json.loads(post_data)
        if 'r' in data and isinstance(data['r'], str):
            data['r'] = data['r'].replace(', or similar', '').strip()
        response = route.fetch(post_data=json.dumps(data))
        body = response.body()
        route.fulfill(body=body, status=response.status, headers=dict(response.headers))
    except Exception:
        route.continue_()


def _sync_afp_route_handler(route):
    """Sync version: inject {result: true} when /s/api/afp returns {}."""
    try:
        response = route.fetch()
        body_bytes = response.body()
        body_text = body_bytes.decode('utf-8', errors='replace').strip()
        if body_text == '{}' or body_text == '':
            route.fulfill(
                body=json.dumps({'result': True}).encode('utf-8'),
                status=200,
                headers={'Content-Type': 'application/json'},
            )
        else:
            route.fulfill(
                body=body_bytes,
                status=response.status,
                headers=dict(response.headers),
            )
    except Exception:
        route.continue_()


def _sync_pixelscan_js_handler(route):
    """Sync version: patch pixelscan JS bundles for osFontsStatus + bot check."""
    try:
        response = route.fetch()
        body = response.body()
        try:
            text = body.decode('utf-8')
        except Exception:
            route.fulfill(body=body, status=response.status, headers=dict(response.headers))
            return
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
            route.fulfill(body=text.encode('utf-8'), status=response.status, headers=headers)
        else:
            route.fulfill(body=body, status=response.status, headers=dict(response.headers))
    except Exception:
        route.continue_()


def _add_sync_routes(target):
    """Register pixelscan route handlers on a sync context or page."""
    target.route('**/s/api/cwg', _sync_cwg_route_handler)
    target.route('**/s/api/afp', _sync_afp_route_handler)
    target.route('**pixelscan.net**.js', _sync_pixelscan_js_handler)


class Foxyz(PlaywrightContextManager):
    """
    Wrapper around playwright.sync_api.PlaywrightContextManager that automatically
    launches a browser and closes it when the context manager is exited.
    """

    def __init__(self, **launch_options):
        super().__init__()
        self.launch_options = launch_options
        self.browser: Optional[Union[Browser, BrowserContext]] = None

    def __enter__(self) -> Union[Browser, BrowserContext]:
        super().__enter__()
        try:
            self.browser = NewBrowser(self._playwright, **self.launch_options)
        except InvalidProxy as e:
            super().__exit__(InvalidProxy, e, None)
            raise
        return self.browser

    def __exit__(self, *args: Any):
        if self.browser:
            self.browser.close()
        super().__exit__(*args)


@overload
def NewBrowser(
    playwright: Playwright,
    *,
    from_options: Optional[Dict[str, Any]] = None,
    persistent_context: Literal[False] = False,
    **kwargs,
) -> Browser: ...


@overload
def NewBrowser(
    playwright: Playwright,
    *,
    from_options: Optional[Dict[str, Any]] = None,
    persistent_context: Literal[True],
    **kwargs,
) -> BrowserContext: ...


class _SyncBrowserWrapper:
    """
    Wraps a Playwright Browser (headless) to inject Foxyz init scripts
    into every new page/context for fingerprint consistency.
    """

    def __init__(self, browser: Browser, font_list: Optional[List[str]] = None) -> None:
        self._browser = browser
        self._init_scripts = (
            make_all_init_scripts(font_list) if font_list else ALL_INIT_SCRIPTS
        )

    def new_context(self, **kwargs: Any) -> BrowserContext:
        ctx = self._browser.new_context(**kwargs)
        ctx.add_init_script(self._init_scripts)
        _add_sync_routes(ctx)
        return ctx

    def new_page(self, **kwargs: Any):
        page = self._browser.new_page(**kwargs)
        page.add_init_script(self._init_scripts)
        _add_sync_routes(page)
        return page

    def close(self, *args: Any, **kwargs: Any) -> None:
        return self._browser.close(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._browser, name)


class _HeadfulBrowserWrapper:
    """
    Wraps a Playwright Browser to inject no_viewport=True into new_context()/new_page()
    calls so the content area follows OS window resize in headful mode.
    Delegates all other attribute access to the underlying browser.
    """

    def __init__(self, browser: Browser, font_list: Optional[List[str]] = None) -> None:
        self._browser = browser
        self._init_scripts = (
            make_all_init_scripts(font_list) if font_list else ALL_INIT_SCRIPTS
        )

    def new_context(self, **kwargs: Any) -> BrowserContext:
        kwargs.setdefault('no_viewport', True)
        ctx = self._browser.new_context(**kwargs)
        ctx.add_init_script(self._init_scripts)
        _add_sync_routes(ctx)
        return ctx

    def new_page(self, **kwargs: Any):
        ctx = self.new_context()
        page = ctx.new_page(**kwargs)
        return page

    def close(self, *args: Any, **kwargs: Any) -> None:
        return self._browser.close(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._browser, name)


def NewBrowser(
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
        from_options = launch_options(headless=headless, debug=debug, **kwargs)

    # Extract OS-specific font list from the launch config for JS font spoofing
    _font_list = _extract_font_list(from_options)

    # Persistent context
    if persistent_context:
        context = playwright.firefox.launch_persistent_context(**from_options)
        if headless is False:
            _macos_activate(from_options.get('executable_path'))
        context = sync_attach_vd(context, virtual_display)
        init_scripts = make_all_init_scripts(_font_list) if _font_list else ALL_INIT_SCRIPTS
        context.add_init_script(init_scripts)
        _add_sync_routes(context)
        return context

    # Browser
    browser = playwright.firefox.launch(**from_options)
    browser = sync_attach_vd(browser, virtual_display)

    # In headful mode, wrap the browser so new_page()/new_context() apply
    # no_viewport=True by default, making the viewport follow OS window resize.
    if headless is False:
        _macos_activate(from_options.get('executable_path'))
        return _HeadfulBrowserWrapper(browser, font_list=_font_list)

    # Headless: wrap to inject init scripts
    return _SyncBrowserWrapper(browser, font_list=_font_list)
