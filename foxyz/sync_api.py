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
        return ctx

    def new_page(self, **kwargs: Any):
        page = self._browser.new_page(**kwargs)
        page.add_init_script(self._init_scripts)
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
