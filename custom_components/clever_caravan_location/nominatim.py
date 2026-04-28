"""Nominatim reverse-geocoding client.

Uses HA's shared aiohttp session and stdlib asyncio.timeout (Python 3.11+).
Respects OSM Nominatim usage policy: User-Agent identification, throttling
handled at the coordinator level, no aggressive retries on failure.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging

import aiohttp

from .const import NOMINATIM_TIMEOUT_S, NOMINATIM_URL, NOMINATIM_USER_AGENT

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeocodeResult:
    """Best-effort fields extracted from Nominatim's response."""

    city: str | None
    state: str | None
    country: str | None
    country_code: str | None
    raw_address: dict | None


async def reverse_geocode(
    session: aiohttp.ClientSession,
    latitude: float,
    longitude: float,
) -> GeocodeResult | None:
    """Look up a place name for the given coordinates.

    Returns None on any failure — caller decides whether to retain
    last good result or null out the sensors.
    """
    params = {
        "lat": f"{latitude:.6f}",
        "lon": f"{longitude:.6f}",
        "format": "jsonv2",
        "zoom": "10",
        "addressdetails": "1",
    }
    headers = {"User-Agent": NOMINATIM_USER_AGENT}

    try:
        async with asyncio.timeout(NOMINATIM_TIMEOUT_S):
            async with session.get(
                NOMINATIM_URL, params=params, headers=headers
            ) as resp:
                if resp.status != 200:
                    _LOGGER.warning(
                        "Nominatim returned HTTP %s for %f,%f",
                        resp.status, latitude, longitude,
                    )
                    return None
                data = await resp.json()
    except (aiohttp.ClientError, TimeoutError) as exc:
        _LOGGER.warning("Nominatim request failed: %s", exc)
        return None

    address = data.get("address") if isinstance(data, dict) else None
    if not address:
        return None

    # Cascading fallback for "city" — Australian remote areas live under
    # different keys (locality, hamlet, town) than urban names (city).
    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("hamlet")
        or address.get("locality")
        or address.get("suburb")
        or address.get("municipality")
        or address.get("county")
    )

    return GeocodeResult(
        city=city,
        state=address.get("state"),
        country=address.get("country"),
        country_code=address.get("country_code"),
        raw_address=address,
    )
