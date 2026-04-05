<div align="center">

<h1>Foxyz</h1>

<p><b>The most consistent browser fingerprint engine on the market.</b></p>

<p>
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#performance">Performance</a> •
  <a href="#api">API</a> •
  <a href="#license">License</a>
</p>

<p>
  <img src="https://img.shields.io/badge/pixelscan-20%2F20_CONSISTENT-brightgreen?style=for-the-badge" alt="Pixelscan Score" />
  <img src="https://img.shields.io/badge/platform-macOS_%7C_Windows_%7C_Linux-blue?style=for-the-badge" alt="Platform" />
  <img src="https://img.shields.io/badge/license-GPL--3.0-orange?style=for-the-badge" alt="License" />
</p>

</div>

---

## Why Foxyz?

Most antidetect browsers fail fingerprint consistency tests. Font manipulation, canvas noise, and WebGL mismatches get flagged instantly by modern detection systems.

**Foxyz doesn't fake fingerprints — it generates real ones.** Every fingerprint is internally consistent across all browser APIs, producing results indistinguishable from a genuine browser on real hardware.

**20/20 CONSISTENT on Pixelscan** — verified across hundreds of test runs with randomized configurations.

---

## Features

- **Full fingerprint consistency** — Canvas, WebGL, Audio, Fonts, Navigator, Screen, WebRTC, Timezone, Geolocation, and Speech Voices all align perfectly
- **Real OS font lists** — No random subsets that trigger font manipulation detectors
- **Per-context isolation** — Each browser context gets a unique, consistent fingerprint
- **Memory saver** — Auto-suspends inactive tabs to keep RAM usage low across multiple profiles
- **Browser-grade UX** — Browsing history, URL suggestions, BFCache (instant back/forward), smooth scrolling
- **Python API** — Sync and async interfaces via Playwright
- **Cross-platform** — macOS, Windows, Linux

---

## Quick Start

### Install

```bash
pip install foxyz
playwright install
```

### Fetch Browser Binary

```bash
python -m foxyz fetch
```

### Usage

```python
from foxyz.sync_api import Foxyz

with Foxyz(headless=False) as browser:
    page = browser.new_page()
    page.goto("https://example.com")
    print(page.title())
```

### Async Usage

```python
from foxyz.async_api import AsyncFoxyz

async with AsyncFoxyz(headless=False) as browser:
    page = await browser.new_page()
    await page.goto("https://example.com")
    print(await page.title())
```

---

## Performance

| Metric | Result |
|--------|--------|
| Pixelscan consistency | **20/20 CONSISTENT** |
| Bot detection | **Not detected** |
| Masking detection | **Not detected** |
| Fingerprint APIs covered | **10+** (Canvas, WebGL, Audio, Fonts, Navigator, Screen, WebRTC, Timezone, Geolocation, Voices) |

---

## API

### Launch Options

```python
Foxyz(
    headless=False,          # Headful mode (default)
    enable_cache=True,       # Browsing history, BFCache, memory cache (default: True)
    block_images=False,      # Block all images
    block_webrtc=False,      # Block WebRTC
    block_webgl=False,       # Block WebGL
    geoip=True,              # Auto-detect geolocation from IP
    humanize=True,           # Human-like input timing
    os="mac",                # Target OS: "mac", "win", "lin"
)
```

### Per-Context Fingerprints

```python
from foxyz.sync_api import Foxyz

with Foxyz(headless=False) as browser:
    context1 = browser.new_context()  # Unique fingerprint
    context2 = browser.new_context()  # Different fingerprint
```

---

## CLI

```bash
foxyz fetch      # Download/install browser binary
foxyz list       # List installed versions
foxyz test       # Open Playwright inspector
foxyz server     # Launch Playwright server
foxyz version    # Display version info
```

---

## Building from Source

### Prerequisites

- Python 3.10+
- Mozilla build dependencies (see `make bootstrap`)
- ~16GB RAM recommended

### Build

```bash
make fetch          # Download Firefox source
make setup          # Setup source directory
make bootstrap      # Install build dependencies
make build          # Build browser
make package-macos  # Package for macOS (or package-linux/package-windows)
```

---

## License

GPL-3.0. See [LICENSE](LICENSE).
