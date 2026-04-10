<div align="center">

# Foxyz

#### Python library for launching and managing Foxyz browser profiles with unique, consistent fingerprints.

</div>

---

## Features

- Unique, consistent browser fingerprints across every session
- Automatic fingerprint generation — OS, CPU, screen, navigator, fonts, headers, WebGL, audio
- Runtime window resize with full fingerprint integrity (iW = oW at all sizes)
- Per-session WebGL hash randomization
- Geolocation, timezone, and locale matching for proxy environments
- Headful and headless modes
- Async and sync API

---

## Installation

```bash
pip install foxyz
foxyz fetch
```

---

## Quick Start

**Async:**

```python
from foxyz.async_api import AsyncFoxyz

async with AsyncFoxyz(headless=False, window=(1280, 800)) as browser:
    page = await browser.new_page()
    await page.goto("https://example.com")
```

**Sync:**

```python
from foxyz.sync_api import NewBrowser
from foxyz.utils import launch_options

opts = launch_options(headless=False, window=(1280, 800))
with NewBrowser(headless=False, from_options=opts) as browser:
    page = browser.new_page()
    page.goto("https://example.com")
```

---

## CLI

```bash
foxyz fetch          # Download the browser
foxyz fetch --help   # See all options
foxyz list           # List installed versions
foxyz remove         # Remove all data
foxyz version        # Show version info
```

---

## Requirements

- Python 3.10+
- macOS arm64 / x64, Windows x64, Linux x64
