import re
import random as _random_module
import secrets
from dataclasses import asdict, dataclass
from random import randrange
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from browserforge.fingerprints import (
    Fingerprint,
    FingerprintGenerator,
    Screen,
    ScreenFingerprint,
)

from foxyz.pkgman import load_yaml

# Load the browserforge.yaml file
BROWSERFORGE_DATA = load_yaml('browserforge.yml')

FP_GENERATOR = FingerprintGenerator(browser='firefox', os=('macos', 'windows'))


# ---------------------------------------------------------------------------
# FingerprintRng — single seeded RNG for all fingerprint randomness.
#
# Mode 1 (fresh identity, default): seed=None → auto-generate unique seed.
# Mode 2 (stable profile): seed=<int> → deterministic across launches.
# ---------------------------------------------------------------------------
class FingerprintRng:
    """
    Thread-safe seeded random number generator for fingerprint generation.

    All randomness that affects fingerprint signals (screen, fonts, voices,
    canvas seed, audio seed, locale, timezone…) must flow through this object
    so that a single ``seed`` value fully reproduces the entire identity.

    Usage::

        # Mode 1 — fresh identity each launch (default Foxyz behaviour)
        rng = FingerprintRng()

        # Mode 2 — stable profile for AntiFoxyz
        rng = FingerprintRng(seed=profile['seed'])
        # save rng.seed alongside the profile to replay later
    """

    __slots__ = ('seed', '_r')

    def __init__(self, seed: Optional[int] = None) -> None:
        self.seed: int = seed if seed is not None else secrets.randbits(48)
        self._r = _random_module.Random(self.seed)

    # ------------------------------------------------------------------
    # Convenience wrappers that mirror the stdlib random module API
    # ------------------------------------------------------------------
    def random(self) -> float:
        return self._r.random()

    def randint(self, a: int, b: int) -> int:
        return self._r.randint(a, b)

    def randrange(self, *args) -> int:  # type: ignore[override]
        return self._r.randrange(*args)

    def choice(self, seq):
        return self._r.choice(seq)

    def choices(self, population, weights=None, k: int = 1):
        return self._r.choices(population, weights=weights, k=k)

    def sample(self, population, k: int):
        return self._r.sample(list(population), k)

    def shuffle(self, x: list) -> None:
        self._r.shuffle(x)

    def numpy_seed(self) -> int:
        """Return a 32-bit seed for numpy (derived from this RNG)."""
        return self.randint(0, 2**32 - 1)


# ---------------------------------------------------------------------------
# Device Tiers — coherent (screen, cores, DPR) bundles.
#
# Each tier represents a real user segment.  All three values are chosen
# together so the fingerprint is internally consistent:
#   • 1366×768 never appears with 32 cores
#   • 4K screen implies high-end hardware
#
# Format per entry: (width, height, dpr)
# ---------------------------------------------------------------------------
_DEVICE_TIERS: List[Dict[str, Any]] = [
    {
        'name': 'budget',
        'weight': 25,
        # Common budget / older laptops
        'screens': [(1366, 768, 1.0), (1280, 768, 1.0), (1280, 800, 1.0)],
        'cores':   [2, 4, 4, 4, 4],          # weighted pool, sample with choice()
        'screen_constraint': Screen(max_width=1366, max_height=768),
    },
    {
        'name': 'mainstream',
        'weight': 40,
        # Standard home / office desktops and laptops
        'screens': [(1920, 1080, 1.0), (1920, 1080, 1.0),
                    (1600, 900, 1.0), (1440, 900, 1.0)],
        'cores':   [4, 4, 8, 8, 8],
        'screen_constraint': Screen(min_width=1440, max_width=1920,
                                    min_height=900,  max_height=1080),
    },
    {
        'name': 'scaled_hd',
        'weight': 15,
        # 1920×1080 display at Windows 125 % DPI scaling → CSS pixels 1536×864
        'screens': [(1536, 864, 1.25)],
        'cores':   [4, 8, 8, 8],
        'screen_constraint': Screen(min_width=1440, max_width=1920,
                                    min_height=900,  max_height=1080),
    },
    {
        'name': 'enthusiast',
        'weight': 15,
        # Developer / power-user machines
        'screens': [(2560, 1440, 1.0), (2560, 1440, 1.0), (1920, 1200, 1.0)],
        'cores':   [8, 8, 12, 16, 16],
        'screen_constraint': Screen(min_width=1920, max_width=2560,
                                    min_height=1080, max_height=1440),
    },
    {
        'name': 'professional',
        'weight': 5,
        # High-end workstations / 4K setups
        'screens': [(3840, 2160, 1.5), (2560, 1440, 2.0), (3840, 2160, 2.0)],
        'cores':   [12, 16, 24, 32, 32],
        'screen_constraint': Screen(min_width=2560, max_width=3840,
                                    min_height=1440, max_height=2160),
    },
]
_TIER_WEIGHTS = [t['weight'] for t in _DEVICE_TIERS]


def pick_device_tier(rng: FingerprintRng) -> Dict[str, Any]:
    """Weighted random sample of a device tier using the session RNG."""
    chosen = rng.choices(_DEVICE_TIERS, weights=_TIER_WEIGHTS, k=1)[0]
    return chosen


def apply_tier_to_fingerprint(fp: Fingerprint, tier: Dict[str, Any],
                               rng: FingerprintRng,
                               target_os: Optional[str] = None) -> None:
    """
    Apply device tier's screen, DPR, and CPU cores to a generated fingerprint.

    BrowserForge is called with the tier's Screen constraint so its Bayesian
    network already produces a correlated UA / GPU.  We then *enforce* the
    exact (width, height, dpr) and hardwareConcurrency from the same tier so
    all three values are always coherent.
    """
    sc = fp.screen
    new_w, new_h, dpr = rng.choice(tier['screens'])
    cores = rng.choice(tier['cores'])

    # OS-specific DPR override
    # macOS: Retina Macs (vast majority) use DPR=2.0; rare non-Retina use 1.0
    # Windows: DPR follows tier (1.0, 1.25, 1.5, 2.0)
    if target_os in ('mac', 'macos'):
        dpr = rng.choices([2.0, 1.0], weights=[85, 15], k=1)[0]

    # Rebuild screen geometry consistently
    taskbar = 40   # Windows taskbar
    avail_h = new_h - taskbar

    chrome_h = (sc.outerHeight - sc.innerHeight) if (sc.outerHeight and sc.innerHeight) else 74
    chrome_w = (sc.outerWidth  - sc.innerWidth)  if (sc.outerWidth  and sc.innerWidth)  else 0

    ratio_w = max(0.70, min((sc.outerWidth  / sc.width)  if sc.width  else 0.90, 0.98))
    ratio_h = max(0.70, min((sc.outerHeight / sc.height) if sc.height else 0.92, 0.98))

    new_outer_w = int(new_w * ratio_w)
    new_outer_h = min(int(new_h * ratio_h), avail_h)
    new_inner_w = max(new_outer_w - chrome_w, 100)
    new_inner_h = max(new_outer_h - chrome_h, 100)

    fp.screen = ExtendedScreen(
        width=new_w, height=new_h,
        availWidth=new_w, availHeight=avail_h,
        availTop=sc.availTop, availLeft=sc.availLeft,
        colorDepth=sc.colorDepth, pixelDepth=sc.pixelDepth,
        devicePixelRatio=dpr,
        pageXOffset=sc.pageXOffset, pageYOffset=sc.pageYOffset,
        outerWidth=new_outer_w, outerHeight=new_outer_h,
        innerWidth=new_inner_w, innerHeight=new_inner_h,
        screenX=sc.screenX,
        clientWidth=sc.clientWidth, clientHeight=sc.clientHeight,
        hasHDR=sc.hasHDR,
        screenY=None,
    )
    # Enforce correlated CPU core count
    fp.navigator.hardwareConcurrency = cores


@dataclass
class ExtendedScreen(ScreenFingerprint):
    """
    An extended version of Browserforge's ScreenFingerprint class
    """

    screenY: Optional[int] = None


def _cast_to_properties(
    foxyz_config: Dict[str, Any],
    cast_enum: Dict[str, Any],
    bf_dict: Dict[str, Any],
    ff_version: Optional[str] = None,
) -> None:
    """
    Casts Browserforge fingerprints to Foxyz config properties.
    """
    for key, data in bf_dict.items():
        # Ignore non-truthy values
        if not data:
            continue
        # Get the associated Foxyz property
        type_key = cast_enum.get(key)
        if not type_key:
            continue
        # If the value is a dictionary, recursively recall
        if isinstance(data, dict):
            _cast_to_properties(foxyz_config, type_key, data, ff_version)
            continue
        # Fix values that are out of bounds
        if type_key.startswith("screen.") and isinstance(data, int) and data < 0:
            data = 0
        # Replace the Firefox versions with ff_version
        if ff_version and isinstance(data, str):
            data = re.sub(r'(?<!\d)(1[0-9]{2})(\.0)(?!\d)', rf'{ff_version}\2', data)
        foxyz_config[type_key] = data


def handle_screenXY(foxyz_config: Dict[str, Any], fp_screen: ScreenFingerprint) -> None:
    """
    Helper method to set window.screenY based on Browserforge's screenX value.
    """
    # Skip if manually provided
    if 'window.screenY' in foxyz_config:
        return
    # Default screenX to 0 if not provided
    screenX = fp_screen.screenX
    if not screenX:
        foxyz_config['window.screenX'] = 0
        foxyz_config['window.screenY'] = 0
        return

    # If screenX is within [-50, 50], use the same value for screenY
    if screenX in range(-50, 51):
        foxyz_config['window.screenY'] = screenX
        return

    # Randomly generate a screenY value based on available screen dimensions.
    screenY = fp_screen.availHeight - fp_screen.outerHeight
    if screenY == 0:
        foxyz_config['window.screenY'] = 0
    elif screenY > 0:
        foxyz_config['window.screenY'] = randrange(0, screenY)  # nosec
    else:
        foxyz_config['window.screenY'] = randrange(screenY, 0)  # nosec


def from_browserforge(fingerprint: Fingerprint, ff_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Converts a Browserforge fingerprint to a Foxyz config.
    """
    foxyz_config: Dict[str, Any] = {}
    _cast_to_properties(
        foxyz_config,
        cast_enum=BROWSERFORGE_DATA,
        bf_dict=asdict(fingerprint),
        ff_version=ff_version,
    )
    handle_screenXY(foxyz_config, fingerprint.screen)

    return foxyz_config


def handle_window_size(fp: Fingerprint, outer_width: int, outer_height: int) -> None:
    """
    Helper method to set a custom outer window size, and center it in the screen
    """
    # Cast the screen to an ExtendedScreen
    fp.screen = ExtendedScreen(**asdict(fp.screen))
    sc = fp.screen

    # Center the window on the screen
    sc.screenX += (sc.width - outer_width) // 2
    sc.screenY = (sc.height - outer_height) // 2

    # Update inner dimensions if set
    if sc.innerWidth:
        sc.innerWidth = max(outer_width - sc.outerWidth + sc.innerWidth, 0)
    if sc.innerHeight:
        sc.innerHeight = max(outer_height - sc.outerHeight + sc.innerHeight, 0)

    # Set outer dimensions
    sc.outerWidth = outer_width
    sc.outerHeight = outer_height


def generate_fingerprint(
    window: Optional[Tuple[int, int]] = None,
    rng: Optional[FingerprintRng] = None,
    **config,
) -> Fingerprint:
    """
    Generate a Firefox fingerprint with BrowserForge.

    When ``rng`` is provided (always the case from ``launch_options``), a
    device tier is picked first so that screen, DPR, and hardware concurrency
    are **coherent with each other**.  BrowserForge is seeded with a value
    derived from ``rng`` so its Bayesian network is also (approximately)
    deterministic for Mode 2 / stable-profile use.

    When ``window`` is explicitly set by the caller, the tier screen override
    is skipped but DPR and cores are still applied from the selected tier.
    """
    if rng is None:
        rng = FingerprintRng()

    # Pick a coherent device tier BEFORE calling BrowserForge so the Screen
    # constraint nudges BrowserForge's correlated signals (UA, GPU…) in the
    # right direction.
    # Only apply tier when no explicit screen constraint is provided.
    # screen=None counts as "no constraint" (user didn't specify one).
    if not window and not config.get('screen'):
        tier = pick_device_tier(rng)
        config['screen'] = tier['screen_constraint']
    else:
        tier = None

    # Seed numpy's global RNG so BrowserForge's Bayesian network is
    # (approximately) deterministic.  We restore the state afterwards so
    # concurrent calls in other threads are not affected.
    np_state = np.random.get_state()
    np.random.seed(rng.numpy_seed())
    try:
        fingerprint = FP_GENERATOR.generate(**config)
    finally:
        np.random.set_state(np_state)

    if window:
        handle_window_size(fingerprint, *window)
    elif tier is not None:
        # Enforce coherent (screen, DPR, cores) from the chosen tier
        # Resolve target OS for DPR override — os may be a string or tuple
        _os_val = config.get('os')
        if isinstance(_os_val, (list, tuple)) and len(_os_val) == 1:
            _os_val = _os_val[0]
        apply_tier_to_fingerprint(fingerprint, tier, rng, target_os=_os_val)

    return fingerprint


if __name__ == "__main__":
    from pprint import pprint

    fp = generate_fingerprint()
    pprint(from_browserforge(fp))
