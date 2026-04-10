<div align="center">

# Foxyz

#### Python library for launching and managing Foxyz browser profiles with unique, consistent fingerprints.

</div>

---

## Installation

**macOS / Linux — paste vào Terminal:**

```bash
curl -fsSL https://raw.githubusercontent.com/foxyzcoding/foxyz/main/install.sh | bash
```

Script tự động:
- Cài Python 3 nếu chưa có
- Cài `foxyz` library
- Download browser binary

**Hoặc cài thủ công:**

```bash
python3 -m pip install foxyz
python3 -m foxyz fetch
```

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
python3 -m foxyz fetch      # Download the browser
python3 -m foxyz list       # List installed versions
python3 -m foxyz remove     # Remove all data
python3 -m foxyz version    # Show version info
```

---

## Requirements

- Python 3.10+
- macOS arm64 / x64, Windows x64, Linux x64
