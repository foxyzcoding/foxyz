import xml.etree.ElementTree as ET  # nosec
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union, cast

import numpy as np
from language_tags import tags

from foxyz.pkgman import LOCAL_DATA, GitHubDownloader, rprint, webdl
from foxyz._warnings import LeakWarning

from .exceptions import (
    InvalidLocale,
    MissingRelease,
    NotInstalledGeoIPExtra,
    UnknownIPLocation,
    UnknownLanguage,
    UnknownTerritory,
)
from .ip import validate_ip

try:
    import geoip2.database  # type: ignore
except ImportError:
    ALLOW_GEOIP = False
else:
    ALLOW_GEOIP = True


"""
Data structures for locale and geolocation info
"""


@dataclass
class Locale:
    """
    Stores locale, region, and script information.
    """

    language: str
    region: Optional[str] = None
    script: Optional[str] = None

    @property
    def as_string(self) -> str:
        if self.region:
            return f"{self.language}-{self.region}"
        return self.language

    def as_config(self) -> Dict[str, str]:
        """
        Converts the locale to a intl config dictionary.
        """
        assert self.region
        data = {
            'locale:region': self.region,
            'locale:language': self.language,
        }
        if self.script:
            data['locale:script'] = self.script
        return data


@dataclass(frozen=True)
class Geolocation:
    """
    Stores geolocation information.
    """

    locale: Locale
    longitude: float
    latitude: float
    timezone: str
    accuracy: Optional[float] = None

    def as_config(self) -> Dict[str, Any]:
        """
        Converts the geolocation to a config dictionary.
        """
        data = {
            'geolocation:longitude': self.longitude,
            'geolocation:latitude': self.latitude,
            'timezone': self.timezone,
            **self.locale.as_config(),
        }
        if self.accuracy:
            data['geolocation:accuracy'] = self.accuracy
        return data


"""
Helpers to validate and normalize locales
"""


def verify_locale(loc: str) -> None:
    """
    Verifies that a locale is valid.
    Takes either language-region or language.
    """
    if tags.check(loc):
        return
    raise InvalidLocale.invalid_input(loc)


def normalize_locale(locale: str) -> Locale:
    """
    Normalizes and validates a locale code.
    """
    verify_locale(locale)

    # Parse the locale
    parser = tags.tag(locale)
    if not parser.region:
        raise InvalidLocale.invalid_input(locale)

    record = parser.language.data['record']

    # Return a formatted locale object
    return Locale(
        language=record['Subtag'],
        region=parser.region.data['record']['Subtag'],
        script=record.get('Suppress-Script'),
    )


def handle_locale(locale: str, ignore_region: bool = False) -> Locale:
    """
    Handles a locale input, normalizing it if necessary.
    """
    # If the user passed in `language-region` or `language-script-region`, normalize it.
    if len(locale) > 3:
        return normalize_locale(locale)

    # Case: user passed in `region` and needs a full locale
    try:
        return SELECTOR.from_region(locale)
    except UnknownTerritory:
        pass

    # Case: user passed in `language`, and doesn't care about the region
    if ignore_region:
        verify_locale(locale)
        return Locale(language=locale)

    # Case: user passed in `language` and wants a region
    try:
        language = SELECTOR.from_language(locale)
    except UnknownLanguage:
        pass
    else:
        LeakWarning.warn('no_region')
        return language

    # Locale is not in a valid format.
    raise InvalidLocale.invalid_input(locale)


# Secondary language fallback probabilities for non-English primary locales.
# Based on real browser telemetry — most non-English Windows users also have
# English as a fallback language in their browser preferences.
_LANG_SECONDARY_FALLBACKS: Dict[str, List[Tuple[str, float]]] = {
    'de': [('en-US', 0.75), ('en', 0.75), ('fr', 0.08)],
    'fr': [('en-US', 0.72), ('en', 0.72)],
    'es': [('en-US', 0.70), ('en', 0.65)],
    'pt': [('en-US', 0.65), ('en', 0.60), ('es', 0.20)],
    'it': [('en-US', 0.68), ('en', 0.65)],
    'nl': [('en-US', 0.85), ('en', 0.85), ('de', 0.15)],
    'pl': [('en-US', 0.70), ('en', 0.70)],
    'ru': [('en-US', 0.55), ('en', 0.50)],
    'zh': [('en-US', 0.60), ('en', 0.55), ('zh-TW', 0.15)],
    'ja': [('en-US', 0.55), ('en', 0.50)],
    'ko': [('en-US', 0.60), ('en', 0.55)],
    'ar': [('en-US', 0.50), ('en', 0.45)],
    'tr': [('en-US', 0.55), ('en', 0.50)],
    'sv': [('en-US', 0.88), ('en', 0.88), ('no', 0.15)],
    'no': [('en-US', 0.88), ('en', 0.88), ('sv', 0.15)],
    'fi': [('en-US', 0.85), ('en', 0.85), ('sv', 0.15)],
    'da': [('en-US', 0.88), ('en', 0.88)],
    'cs': [('en-US', 0.65), ('en', 0.65), ('sk', 0.20)],
    'sk': [('en-US', 0.65), ('en', 0.65), ('cs', 0.20)],
    'hu': [('en-US', 0.62), ('en', 0.60)],
    'ro': [('en-US', 0.60), ('en', 0.58), ('fr', 0.15)],
    'vi': [('en-US', 0.55), ('en', 0.50)],
    'th': [('en-US', 0.55), ('en', 0.50)],
    'id': [('en-US', 0.65), ('en', 0.62)],
    'ms': [('en-US', 0.72), ('en', 0.70)],
    'uk': [('en-US', 0.52), ('en', 0.48), ('ru', 0.35)],
}


def _build_languages_array(primary_locale: Locale, rng=None) -> str:
    """
    Build a realistic navigator.languages-style string for locale:all.

    Single-locale case only — multi-locale input goes through the explicit path.
    Examples:
      en-US → "en-US, en"
      de-DE → "de-DE, de, en-US, en"   (75% of the time)
              "de-DE, de"               (25% of the time)
      en-GB → "en-GB, en, en-US"        (40% of the time)
              "en-GB, en"               (60% of the time)
    """
    import random  # nosec

    lang = primary_locale.language.lower()
    region = primary_locale.region or ''
    primary_str = primary_locale.as_string  # e.g. "de-DE"

    langs: List[str] = [primary_str]

    # Add bare language code when region is present (e.g. "de" for "de-DE")
    if region and lang not in langs:
        langs.append(lang)

    if lang == 'en':
        # English-region locales: optionally append en-US as tertiary fallback
        # (en-US users never need en-US as fallback — they already are it)
        if region and region.upper() != 'US':
            if random.random() < 0.40:  # nosec
                langs.append('en-US')
    else:
        # Non-English: probabilistically add secondary languages
        fallbacks = _LANG_SECONDARY_FALLBACKS.get(
            lang,
            [('en-US', 0.60), ('en', 0.55)],  # default for unknown languages
        )
        _rand = rng.random if rng is not None else random.random
        for secondary, probability in fallbacks:
            if secondary not in langs and _rand() < probability:
                langs.append(secondary)

    return ', '.join(langs)


def handle_locales(locales: Union[str, List[str]], config: Dict[str, Any],
                   rng=None) -> None:
    """
    Handles a list of locales.
    ``rng`` is the session FingerprintRng; pass it so navigator.languages
    expansion is deterministic in Mode 2 (stable-profile) use.
    """
    if isinstance(locales, str):
        locales = [loc.strip() for loc in locales.split(',')]

    # First, handle the first locale. This will be used for the intl api.
    intl_locale = handle_locale(locales[0])
    config.update(intl_locale.as_config())

    if len(locales) >= 2:
        # User explicitly provided multiple locales — use them verbatim.
        config['locale:all'] = _join_unique(
            handle_locale(locale, ignore_region=True).as_string for locale in locales
        )
    elif 'locale:all' not in config:
        # Single locale: generate a realistic navigator.languages array.
        config['locale:all'] = _build_languages_array(intl_locale, rng=rng)


def _join_unique(seq: Iterable[str]) -> str:
    """
    Joins a sequence of strings without duplicates
    """
    seen: Set[str] = set()
    return ', '.join(x for x in seq if not (x in seen or seen.add(x)))


"""
Helpers to fetch geolocation, timezone, and locale data given an IP.
"""

MMDB_FILE = LOCAL_DATA / 'GeoLite2-City.mmdb'
MMDB_REPO = "P3TERX/GeoLite.mmdb"


class MaxMindDownloader(GitHubDownloader):
    """
    MaxMind database downloader from a GitHub repository.
    """

    def check_asset(self, asset: Dict, release: Optional[Dict] = None) -> Optional[str]:
        # Check for the first -City.mmdb file
        if asset['name'].endswith('-City.mmdb'):
            return asset['browser_download_url']
        return None

    def missing_asset_error(self) -> None:
        raise MissingRelease('Failed to find GeoIP database release asset')


def geoip_allowed() -> None:
    """
    Checks if the geoip2 module is available.
    """
    if not ALLOW_GEOIP:
        raise NotInstalledGeoIPExtra(
            'Please install the geoip extra to use this feature: pip install foxyz[geoip]'
        )


def download_mmdb() -> None:
    """
    Downloads the MaxMind GeoIP2 database.
    """
    geoip_allowed()

    asset_url = MaxMindDownloader(MMDB_REPO).get_asset()

    with open(MMDB_FILE, 'wb') as f:
        webdl(
            asset_url,
            desc='Downloading GeoIP database',
            buffer=f,
        )


def remove_mmdb() -> None:
    """
    Removes the MaxMind GeoIP2 database.
    """
    if not MMDB_FILE.exists():
        rprint("GeoIP database not found.")
        return

    MMDB_FILE.unlink()
    rprint("GeoIP database removed.")


def get_geolocation(ip: str) -> Geolocation:
    """
    Gets the geolocation for an IP address.
    """
    # Check if the database is downloaded
    if not MMDB_FILE.exists():
        download_mmdb()

    # Validate the IP address
    validate_ip(ip)

    with geoip2.database.Reader(str(MMDB_FILE)) as reader:
        resp = reader.city(ip)
        iso_code = cast(str, resp.registered_country.iso_code).upper()
        location = resp.location

        # Check if any required attributes are missing
        if any(not getattr(location, attr) for attr in ('longitude', 'latitude', 'time_zone')):
            raise UnknownIPLocation(f"Unknown IP location: {ip}")

        # Get a statistically correct locale based on the country code
        locale = SELECTOR.from_region(iso_code)

        return Geolocation(
            locale=locale,
            longitude=cast(float, resp.location.longitude),
            latitude=cast(float, resp.location.latitude),
            timezone=cast(str, resp.location.time_zone),
        )


"""
Gets a random language based on the territory code.
"""


def get_unicode_info() -> ET.Element:
    """
    Fetches supplemental data from the territoryInfo.xml file.
    Source: https://raw.githubusercontent.com/unicode-org/cldr/master/common/supplemental/supplementalData.xml
    """
    with open(LOCAL_DATA / 'territoryInfo.xml', 'rb') as f:
        data = ET.XML(f.read())
    assert data is not None, 'Failed to load territoryInfo.xml'
    return data


def _as_float(element: ET.Element, attr: str) -> float:
    """
    Converts an attribute to a float.
    """
    return float(element.get(attr, 0))


class StatisticalLocaleSelector:
    """
    Selects a random locale based on statistical data.
    Takes either a territory code or a language code, and generates a Locale object.
    """

    def __init__(self):
        self.root = get_unicode_info()

    def _load_territory_data(self, iso_code: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculates a random language based on the territory code,
        based on the probability that a person speaks the language in the territory.
        """
        territory = self.root.find(f"territory[@type='{iso_code}']")
        if territory is None:
            raise UnknownTerritory(f"Unknown territory: {iso_code}")

        lang_populations = territory.findall('languagePopulation')
        if not lang_populations:
            raise ValueError(f"No language data found for region: {iso_code}")

        languages = np.array([lang.get('type') for lang in lang_populations])
        percentages = np.array([_as_float(lang, 'populationPercent') for lang in lang_populations])

        return self.normalize_probabilities(languages, percentages)

    def _load_language_data(self, language: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculates a random region for a language
        based on the total speakers of the language in that region.
        """
        territories = self.root.findall(f'.//territory/languagePopulation[@type="{language}"]/..')
        if not territories:
            raise UnknownLanguage(f"No region data found for language: {language}")

        regions = []
        percentages = []

        for terr in territories:
            region = terr.get('type')
            if region is None:
                continue  # Skip if region is not found

            lang_pop = terr.find(f'languagePopulation[@type="{language}"]')
            if lang_pop is None:
                continue  # This shouldn't happen due to our XPath, but just in case

            regions.append(region)
            percentages.append(
                _as_float(lang_pop, 'populationPercent')
                * _as_float(terr, 'literacyPercent')
                / 10_000
                * _as_float(terr, 'population')
            )

        if not regions:
            raise ValueError(f"No valid region data found for language: {language}")

        return self.normalize_probabilities(np.array(regions), np.array(percentages))

    def normalize_probabilities(
        self, languages: np.ndarray, freq: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Normalize probabilities.
        """
        total = np.sum(freq)
        return languages, freq / total

    def from_region(self, region: str) -> Locale:
        """
        Get a random locale based on the territory ISO code.
        Returns as a Locale object.
        """
        languages, probabilities = self._load_territory_data(region)
        language = np.random.choice(languages, p=probabilities).replace('_', '-')
        return normalize_locale(f"{language}-{region}")

    def from_language(self, language: str) -> Locale:
        """
        Get a random locale based on the language.
        Returns as a Locale object.
        """
        regions, probabilities = self._load_language_data(language)
        region = np.random.choice(regions, p=probabilities)
        return normalize_locale(f"{language}-{region}")


SELECTOR = StatisticalLocaleSelector()
