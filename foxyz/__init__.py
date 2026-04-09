from .addons import DefaultAddons
from .async_api import AsyncFoxyz, AsyncNewBrowser
from .sync_api import Foxyz, NewBrowser
from .utils import launch_options

__all__ = [
    "Foxyz",
    "NewBrowser",
    "AsyncFoxyz",
    "AsyncNewBrowser",
    "DefaultAddons",
    "launch_options",
]
