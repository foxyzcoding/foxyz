"""
GeoIP helpers for Foxyz.
Core get_geolocation / geoip_allowed / download_mmdb logic lives in locales.py
(aligned with Camoufox's locale.py).
This module re-exports those and provides Foxyz CLI management shims.
"""
from .locales import (
    ALLOW_GEOIP,
    MMDB_FILE,
    MMDB_REPO,
    MaxMindDownloader,
    download_mmdb,
    get_geolocation,
    geoip_allowed,
    remove_mmdb,
)
from .pkgman import LOCAL_DATA

# ── CLI-facing path constants ─────────────────────────────────────────────────
# The mmdb now lives at LOCAL_DATA / 'GeoLite2-City.mmdb' (Camoufox-style).
# GEOIP_DIR points to the same folder so __main__.py path checks still work.
GEOIP_DIR = LOCAL_DATA


# ── CLI management shims ──────────────────────────────────────────────────────

def get_mmdb_path(ip_version: str = 'ipv4', config=None):
    """Return path to the GeoIP mmdb file."""
    return MMDB_FILE


def load_geoip_config() -> dict:
    """Return the active GeoIP config (simplified: single Camoufox-style source)."""
    return {'name': 'GeoLite2', 'repo': MMDB_REPO}


def save_geoip_config(config: dict) -> None:
    """No-op: config is implicit (Camoufox-style single file at LOCAL_DATA)."""
    pass


def _load_geoip_repos():
    """Return (repos_list, default_name) for CLI GeoIP source selection."""
    repos = [{'name': 'GeoLite2', 'repo': MMDB_REPO}]
    return repos, 'GeoLite2'


__all__ = [
    # Re-exports from locales.py
    'ALLOW_GEOIP',
    'MMDB_FILE',
    'MMDB_REPO',
    'MaxMindDownloader',
    'download_mmdb',
    'get_geolocation',
    'geoip_allowed',
    'remove_mmdb',
    # Foxyz CLI shims
    'GEOIP_DIR',
    'get_mmdb_path',
    'load_geoip_config',
    'save_geoip_config',
    '_load_geoip_repos',
]
