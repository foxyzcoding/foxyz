"""
Manager for handling multiple Foxyz versions side by side
"""

import os
import plistlib
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from .pkgman import AvailableVersion

import orjson
import rich_click as click

from .pkgman import INSTALL_DIR, OS_NAME, Version, rprint, unzip

BROWSERS_DIR: Path = INSTALL_DIR / "browsers"
CONFIG_FILE: Path = INSTALL_DIR / "config.json"
REPO_CACHE_FILE: Path = INSTALL_DIR / "repo_cache.json"
COMPAT_FLAG: Path = INSTALL_DIR / ".0.5_FLAG"


def load_config() -> Dict:
    """
    Load user config from disk, or return empty dict
    """
    if CONFIG_FILE.exists():
        try:
            return orjson.loads(CONFIG_FILE.read_bytes())
        except orjson.JSONDecodeError:
            pass
    return {}


def get_default_channel() -> str:
    """
    Get the default repo's stable channel string (like official/stable)
    """
    from .pkgman import RepoConfig

    return f"{RepoConfig.get_default_name().lower()}/stable"


def save_config(config: Dict) -> None:
    """
    Save user config to disk
    """
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_bytes(orjson.dumps(config, option=orjson.OPT_INDENT_2))


def load_repo_cache() -> Dict:
    """
    Load cached repo data from disk
    """
    if REPO_CACHE_FILE.exists():
        try:
            return orjson.loads(REPO_CACHE_FILE.read_bytes())
        except orjson.JSONDecodeError:
            pass
    return {}


def save_repo_cache(cache: Dict) -> None:
    """
    Save repo cache to disk
    """
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    REPO_CACHE_FILE.write_bytes(orjson.dumps(cache, option=orjson.OPT_INDENT_2))


def get_cached_versions(repo_name: Optional[str] = None) -> List['AvailableVersion']:
    """
    Get cached available versions, optionally filtered by repo
    """
    from .pkgman import AvailableVersion, Version

    cache = load_repo_cache()
    if not cache.get('repos'):
        return []

    versions = []
    for repo_data in cache['repos']:
        if repo_name and repo_data['name'].lower() != repo_name.lower():
            continue
        for v in repo_data.get('versions', []):
            versions.append(
                AvailableVersion(
                    version=Version(build=v['build'], version=v['version']),
                    url=v['url'],
                    is_prerelease=v.get('is_prerelease', False),
                    asset_id=v.get('asset_id'),
                    asset_size=v.get('asset_size'),
                    asset_updated_at=v.get('asset_updated_at'),
                )
            )

    versions.sort(key=lambda x: x.version, reverse=True)
    return versions


def get_cached_repo_names() -> List[str]:
    """
    Get list of repo names in cache
    """
    cache = load_repo_cache()
    return [r['name'] for r in cache.get('repos', [])]


def get_repo_name(github_repo: str) -> str:
    """
    Get display name for a repo from repos.yml, lowercased
    """
    from .pkgman import RepoConfig

    for repo in RepoConfig.load_repos():
        if github_repo in repo.repos:
            return repo.name.lower()
    return github_repo.split('/')[0].lower()


@dataclass
class InstalledVersion:
    """
    Information about an installed Foxyz version
    """

    repo_name: str
    version: Version
    path: Path
    is_active: bool = False
    is_prerelease: bool = False
    asset_id: Optional[int] = None
    asset_size: Optional[int] = None
    asset_updated_at: Optional[str] = None

    @property
    def relative_path(self) -> str:
        """
        Path relative to INSTALL_DIR (like browsers/official/134.0.2-beta.20)
        """
        return f"browsers/{self.repo_name}/{self.version.full_string}"

    @property
    def channel_path(self) -> str:
        """
        Channel display string (like official/stable/134.0.2-beta.20)
        """
        ctype = "prerelease" if self.is_prerelease else "stable"
        return f"{self.repo_name}/{ctype}/{self.version.full_string}"

    def get_changes(self, available: 'AvailableVersion') -> List[str]:
        """
        Compare with an available version and return change indicators
        """
        changes: List[str] = []
        if self.is_prerelease and not available.is_prerelease:
            changes.append("prerelease -> stable")
        elif not self.is_prerelease and available.is_prerelease:
            changes.append("stable -> prerelease")

        if self.asset_updated_at and available.asset_updated_at:
            if self.asset_updated_at != available.asset_updated_at:
                changes.append("asset updated")
        elif self.asset_size and available.asset_size:
            if self.asset_size != available.asset_size:
                changes.append("asset updated")

        return changes


def find_installed_by_build(
    build: str, repo_name: Optional[str] = None
) -> Optional[InstalledVersion]:
    """
    Find an installed version by its build string
    """
    for v in list_installed():
        if v.version.build == build:
            if repo_name is None or v.repo_name == repo_name:
                return v
    return None


def list_installed() -> List[InstalledVersion]:
    """
    Scan browsers/ for installed versions, sorted by repo then version descending
    """
    installed: List[InstalledVersion] = []
    config = load_config()
    active = config.get('active_version')

    if not BROWSERS_DIR.exists():
        return installed

    for repo_dir in BROWSERS_DIR.iterdir():
        if not repo_dir.is_dir() or repo_dir.name.startswith('.'):
            continue

        for version_dir in repo_dir.iterdir():
            if not version_dir.is_dir():
                continue

            version_json = version_dir / 'version.json'
            if not version_json.exists():
                continue

            try:
                ver = Version.from_path(version_dir)
                with open(version_json, 'rb') as f:
                    version_data = orjson.loads(f.read())
                rel_path = f"browsers/{repo_dir.name}/{ver.full_string}"
                installed.append(
                    InstalledVersion(
                        repo_name=repo_dir.name,
                        version=ver,
                        path=version_dir,
                        is_active=(rel_path == active),
                        is_prerelease=version_data.get('prerelease', False),
                        asset_id=version_data.get('asset_id'),
                        asset_size=version_data.get('asset_size'),
                        asset_updated_at=version_data.get('asset_updated_at'),
                    )
                )
            except (FileNotFoundError, orjson.JSONDecodeError):
                continue

    installed.sort(key=lambda x: (x.repo_name, x.version), reverse=True)
    return installed


def get_active_path() -> Optional[Path]:
    """
    Get path to active version. Returns None if no version is active.
    Only auto-selects if no channel/pin was been set
    """
    config = load_config()
    active = config.get('active_version')

    if active:
        path = INSTALL_DIR / active
        if path.exists() and (path / 'version.json').exists():
            return path

    # Only auto-select if user didnt set a channel or pin
    if not config.get('channel') and not config.get('pinned'):
        installed = list_installed()
        if installed:
            config['active_version'] = installed[0].relative_path
            save_config(config)
            return installed[0].path

    return None


def set_active(relative_path: str) -> None:
    """
    Set the active version by its relative path
    """
    config = load_config()
    config['active_version'] = relative_path
    save_config(config)


def find_installed_version(specifier: str) -> Optional[Path]:
    """
    Find an installed version by path, build, full version, or repo/build
    """
    installed = list_installed()
    if not installed:
        return None

    specifier_lower = specifier.lower()

    for v in installed:
        if v.relative_path == specifier or v.relative_path == f"browsers/{specifier}":
            return v.path
        if f"browsers/{v.repo_name}/{v.version.full_string}".endswith(specifier):
            return v.path
        if f"{v.repo_name}/{v.version.build}".lower() == specifier_lower:
            return v.path
        if v.version.build.lower() == specifier_lower:
            return v.path
        if v.version.full_string.lower() == specifier_lower:
            return v.path
        if v.version.version and v.version.version.lower() == specifier_lower:
            return v.path

    return None


def _patch_browser_omni_ja(app_dir: Path) -> None:
    """
    Patch browser/omni.ja inside the .app bundle:
    - Replace "Camoufox" with "Foxyz" in brand.ftl (fixes Settings title, tab names, etc.)
    - Replace branding icon PNGs with Foxyz ones (fixes tab logo on internal pages)
    """
    import zipfile

    omni_path = app_dir / 'Contents' / 'Resources' / 'browser' / 'omni.ja'
    if not omni_path.exists():
        return

    # Locate the additions/browser/branding/foxyz directory
    branding_candidates = [
        Path(__file__).parent.parent.parent.parent / 'additions' / 'browser' / 'branding' / 'foxyz',
        Path.home() / 'Desktop' / 'Foxyz' / 'additions' / 'browser' / 'branding' / 'foxyz',
    ]
    branding_dir: Optional[Path] = None
    for candidate in branding_candidates:
        if (candidate / 'default16.png').exists():
            branding_dir = candidate
            break

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            with zipfile.ZipFile(omni_path, 'r') as zf:
                zf.extractall(tmp)

            modified = False

            # 1. Patch brand strings (FTL + legacy .properties files)
            text_files = [
                tmp / 'localization' / 'en-US' / 'branding' / 'brand.ftl',
                tmp / 'chrome' / 'en-US' / 'locale' / 'branding' / 'brand.properties',
                tmp / 'chrome' / 'en-US' / 'locale' / 'browser' / 'appstrings.properties',
            ]
            for tf in text_files:
                if tf.exists():
                    content = tf.read_text(encoding='utf-8')
                    new_content = content.replace('Camoufox', 'Foxyz')
                    if new_content != content:
                        tf.write_text(new_content, encoding='utf-8')
                        modified = True

            # 2. Replace branding icons
            if branding_dir:
                icon_dst = tmp / 'chrome' / 'browser' / 'content' / 'branding'
                icon_map = {
                    'icon16.png': branding_dir / 'default16.png',
                    'icon32.png': branding_dir / 'default32.png',
                    'icon48.png': branding_dir / 'default48.png',
                    'icon64.png': branding_dir / 'default64.png',
                    'icon128.png': branding_dir / 'default128.png',
                    'about-logo.png': branding_dir / 'content' / 'about-logo.png',
                    'about-logo@2x.png': branding_dir / 'content' / 'about-logo@2x.png',
                    'about-logo.svg': branding_dir / 'content' / 'about-logo.svg',
                    'about-wordmark.svg': branding_dir / 'content' / 'about-wordmark.svg',
                    'about.png': branding_dir / 'content' / 'about.png',
                    'firefox-wordmark.svg': branding_dir / 'content' / 'firefox-wordmark.svg',
                }
                for dst_name, src in icon_map.items():
                    dst = icon_dst / dst_name
                    if src.exists() and dst.exists():
                        shutil.copy2(src, dst)
                        modified = True

            if modified:
                new_omni = Path(tmpdir) / 'new_omni.ja'
                subprocess.run(
                    ['zip', '-0', '-r', str(new_omni), '.'],
                    cwd=str(tmp),
                    capture_output=True,
                    check=True,
                )
                shutil.copy2(new_omni, omni_path)
    except Exception:
        pass  # Non-critical: branding patch is best-effort


def _inject_bundled_fonts(install_path: Path) -> None:
    """
    Copy cross-OS fonts from the local bundle/ directory into the installed
    browser so that any target-OS profile renders fonts correctly regardless
    of the host OS.

    Mechanism per host OS:
    - macOS: Firefox CoreText reads `Contents/Resources/fonts/` when
             gfx.bundled-fonts.activate=1.  We inject Windows fonts there.
    - Windows: DWrite reads `fonts/` from the install root.  We inject macOS
               fonts there.

    The operation is idempotent: if `fonts/` is already non-empty it is skipped.
    """
    # ── Locate bundle/ directory ─────────────────────────────────────────────
    bundle_candidates = [
        Path(__file__).parent.parent.parent.parent / 'bundle',
        Path.home() / 'Desktop' / 'Foxyz' / 'bundle',
        Path.home() / 'Desktop' / 'foxyz-browser' / 'bundle',
    ]
    bundle_dir: Optional[Path] = None
    for c in bundle_candidates:
        if c.is_dir() and (c / 'fonts').is_dir():
            bundle_dir = c
            break
    if bundle_dir is None:
        rprint(
            "[yellow]Warning: bundle/fonts not found — cross-OS font injection skipped.[/yellow]"
        )
        return

    # ── Determine install root and fonts destination ─────────────────────────
    if OS_NAME == 'mac':
        # Resolve the .app bundle (may be named Foxyz.app or Camoufox.app)
        app_dir: Optional[Path] = None
        for name in ('Foxyz.app', 'Camoufox.app'):
            candidate = install_path / name
            if candidate.is_dir():
                app_dir = candidate
                break
        if app_dir is None:
            return
        resources_dir = app_dir / 'Contents' / 'Resources'
        fonts_dest = resources_dir / 'fonts'
        fontconfig_dest = None           # macOS uses CoreText — no fontconfig needed
        font_sources = ['windows']       # macOS system fonts cover 'macos'

    else:  # win
        fonts_dest = install_path / 'fonts'
        fontconfig_dest = None           # Windows uses DWrite — no fontconfig needed
        font_sources = ['macos']

    # ── Inject font files (flat layout) ──────────────────────────────────────
    if fonts_dest.exists() and any(fonts_dest.iterdir()):
        rprint(f"[dim]Bundled fonts already present at {fonts_dest} — skipping.[/dim]")
    else:
        fonts_dest.mkdir(parents=True, exist_ok=True)
        total = 0
        for os_name in font_sources:
            src_dir = bundle_dir / 'fonts' / os_name
            if not src_dir.is_dir():
                continue
            for f in src_dir.iterdir():
                if f.suffix.lower() in ('.ttf', '.otf', '.ttc', '.otc'):
                    shutil.copy2(f, fonts_dest / f.name)
                    total += 1
        rprint(f"[green]Injected {total} bundled font files → {fonts_dest}[/green]")


def _rebrand_mac_app(install_path: Path) -> None:
    """
    Rebrand the browser app bundle to Foxyz.app on macOS.
    Patches Info.plist and replaces the app icon with the Foxyz logo.
    """
    if OS_NAME != 'mac':
        return

    old_app = install_path / 'Camoufox.app'
    new_app = install_path / 'Foxyz.app'

    # Determine which .app exists
    if new_app.exists():
        app_dir = new_app
    elif old_app.exists():
        app_dir = old_app
    else:
        return

    # Patch Info.plist
    plist_path = app_dir / 'Contents' / 'Info.plist'
    if plist_path.exists():
        with open(plist_path, 'rb') as f:
            plist = plistlib.load(f)
        plist['CFBundleName'] = 'Foxyz'
        plist['CFBundleDisplayName'] = 'Foxyz'  # shown in macOS notifications & Finder
        plist['CFBundleIdentifier'] = 'com.foxyz.browser'
        if 'CFBundleGetInfoString' in plist:
            plist['CFBundleGetInfoString'] = plist['CFBundleGetInfoString'].replace(
                'Camoufox', 'Foxyz'
            )
        with open(plist_path, 'wb') as f:
            plistlib.dump(plist, f)

    # Replace icon with Foxyz logo if available
    logo_candidates = [
        Path(__file__).parent / 'gui' / 'assets' / 'browserlogo.png',  # bundled in package
        Path(__file__).parent.parent.parent.parent / 'browserlogo.png',  # repo root
        Path.home() / 'Desktop' / 'Foxyz' / 'browserlogo.png',
    ]
    logo_src = None
    for candidate in logo_candidates:
        if candidate.exists():
            logo_src = candidate
            break

    if logo_src:
        icon_path = app_dir / 'Contents' / 'Resources' / 'firefox.icns'
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                iconset = Path(tmpdir) / 'foxyz.iconset'
                iconset.mkdir()
                sizes = [
                    (16, 'icon_16x16.png'), (32, 'icon_16x16@2x.png'),
                    (32, 'icon_32x32.png'), (64, 'icon_32x32@2x.png'),
                    (128, 'icon_128x128.png'), (256, 'icon_128x128@2x.png'),
                    (256, 'icon_256x256.png'), (512, 'icon_256x256@2x.png'),
                    (512, 'icon_512x512.png'), (1024, 'icon_512x512@2x.png'),
                ]
                for size, name in sizes:
                    subprocess.run(
                        ['sips', '-z', str(size), str(size), str(logo_src),
                         '--out', str(iconset / name)],
                        capture_output=True
                    )
                icns_out = Path(tmpdir) / 'foxyz.icns'
                subprocess.run(
                    ['iconutil', '-c', 'icns', str(iconset), '-o', str(icns_out)],
                    capture_output=True
                )
                if icns_out.exists():
                    shutil.copy2(icns_out, icon_path)
                    # Also replace document.icns
                    doc_icon = app_dir / 'Contents' / 'Resources' / 'document.icns'
                    if doc_icon.exists():
                        shutil.copy2(icns_out, doc_icon)
        except Exception:
            pass  # Non-critical: icon replacement is best-effort

    # Inject local-settings.js so foxyz.cfg is loaded (disables sidebar, etc.)
    resources = app_dir / 'Contents' / 'Resources'
    pref_dir = resources / 'defaults' / 'pref'
    pref_dir.mkdir(parents=True, exist_ok=True)
    local_settings = pref_dir / 'local-settings.js'
    if not local_settings.exists():
        local_settings.write_text(
            '// Tell Firefox to load foxyz.cfg\n'
            'pref("general.config.filename", "foxyz.cfg");\n'
            'pref("general.config.obscure_value", 0);\n'
        )

    # Sync chrome.css and foxyz.cfg from the repo settings/ directory into the binary
    # so that UI customizations (tab bar, sidebar, etc.) are always up-to-date.
    settings_candidates = [
        Path(__file__).parent.parent.parent.parent / 'settings',
        Path.home() / 'Desktop' / 'Foxyz' / 'settings',
    ]
    settings_dir = None
    for candidate in settings_candidates:
        if (candidate / 'chrome.css').exists():
            settings_dir = candidate
            break
    if settings_dir:
        for fname in ('chrome.css', 'foxyz.cfg'):
            src = settings_dir / fname
            dst = resources / fname
            if src.exists():
                shutil.copy2(src, dst)
        # Sync policies.json (controls search engines, extensions, etc.)
        policies_src = settings_dir / 'distribution' / 'policies.json'
        policies_dst = resources / 'distribution' / 'policies.json'
        if policies_src.exists() and policies_dst.exists():
            shutil.copy2(policies_src, policies_dst)

    # Patch browser/omni.ja: fix brand name strings and replace branding icons
    _patch_browser_omni_ja(app_dir)

    # Rename .app bundle
    if app_dir == old_app and not new_app.exists():
        old_app.rename(new_app)


def install_versioned(fetcher, replace: bool = False) -> bool:
    """
    Install to browsers/{repo_name}/{version}-{build}/
    """
    repo_name = get_repo_name(fetcher.github_repo)
    version_folder = f"{fetcher.version}-{fetcher.build}"
    install_path = BROWSERS_DIR / repo_name / version_folder

    if install_path.exists() and (install_path / 'version.json').exists():
        if not replace:
            installed_v = find_installed_by_build(fetcher.build, repo_name)
            change_msg = ""
            if installed_v and fetcher._selected_version:
                changes = installed_v.get_changes(fetcher._selected_version)
                if changes:
                    change_msg = f" ({', '.join(changes)})"

            rprint(f"Version v{fetcher.verstr} already installed{change_msg}.", fg="yellow")
            if change_msg:
                rprint("Use --replace to update with the new release.", fg="yellow")
            else:
                rprint("Use --replace to reinstall.", fg="yellow")
            if not load_config().get('active_version'):
                set_active(f"browsers/{repo_name}/{version_folder}")
            return False
        rprint(f"Replacing: {install_path}", fg="yellow")
        shutil.rmtree(install_path)

    try:
        install_path.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile() as temp_file:
            fetcher.download_file(temp_file, fetcher.url)
            rprint(f'Extracting Foxyz: {install_path}')
            unzip(temp_file, str(install_path))

            if fetcher._selected_version:
                metadata = fetcher._selected_version.to_metadata()
            else:
                metadata = {
                    'version': fetcher.version,
                    'build': fetcher.build,
                    'prerelease': fetcher.is_prerelease,
                }
            with open(install_path / 'version.json', 'wb') as f:
                f.write(orjson.dumps(metadata))

        if OS_NAME != 'win':
            os.system(f'chmod -R 755 {shlex.quote(str(install_path))}')  # nosec

        # Apply Foxyz branding to the app bundle
        _rebrand_mac_app(install_path)

        # Inject cross-OS bundled fonts so any target-OS profile renders
        # fonts correctly regardless of the host OS.
        _inject_bundled_fonts(install_path)

        set_active(f"browsers/{repo_name}/{version_folder}")

        # Mark the install dir as compatible with this version
        COMPAT_FLAG.touch()

        rprint(f'\nFoxyz v{fetcher.verstr} installed.', fg="green")
        rprint(f'Path: {install_path}', fg="green")
        return True

    except Exception as e:
        rprint(f"Error: {e}", fg="red")
        if install_path.exists():
            shutil.rmtree(install_path)
        raise


def remove_version(path: Path) -> bool:
    """
    Remove a specific version installation
    """
    if not path.exists():
        return False

    rprint(f'Removing: {path}')
    shutil.rmtree(path)

    parent = path.parent
    if parent.exists() and parent != BROWSERS_DIR and not any(parent.iterdir()):
        parent.rmdir()
    if BROWSERS_DIR.exists() and not any(BROWSERS_DIR.iterdir()):
        BROWSERS_DIR.rmdir()

    config = load_config()
    try:
        rel_path = str(path.relative_to(INSTALL_DIR))
        if config.get('active_version') == rel_path:
            remaining = list_installed()
            config['active_version'] = remaining[0].relative_path if remaining else None
            save_config(config)
    except ValueError:
        pass  # Path not relative to INSTALL_DIR

    return True


def print_tree(show_header: bool = True, show_paths: bool = False) -> None:
    """
    Print installed versions as a tree
    """
    installed = list_installed()

    if not installed:
        rprint("No versions installed.", fg="yellow")
        rprint("Run `foxyz fetch` to install.", fg="yellow")
        return

    if show_header:
        rprint("Installed versions:\n", fg="yellow")

    current_repo = None
    for i, v in enumerate(installed):
        is_last = (i == len(installed) - 1) or (installed[i + 1].repo_name != v.repo_name)

        if v.repo_name != current_repo:
            current_repo = v.repo_name
            click.secho(f"{current_repo}/", fg="cyan", bold=True, nl=False)
            if show_paths:
                click.secho(f" -> {BROWSERS_DIR / current_repo}", fg="bright_black")
            else:
                click.echo()

        branch = "└── " if is_last else "├── "
        color = "green" if v.is_active else None

        click.echo(f"    {branch}", nl=False)
        click.secho(f"v{v.version.full_string}", fg=color, bold=v.is_active, nl=False)
        if v.is_prerelease:
            click.secho(" (prerelease)", fg="yellow", nl=False)
        else:
            click.secho(" (stable)", fg="blue", nl=False)
        if v.is_active:
            click.secho(" (active)", fg="green", bold=True, nl=False)
        click.echo()
