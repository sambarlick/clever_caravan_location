"""ABS Digital Atlas SA2 lookup.

Single API call against the ABS Census G01 SA2 layer returns the SA2
polygon containing the given lat/long, with population (Tot_P_P) and
area (areasqkm_2021) attributes joined.

Endpoint is hosted by ABS in partnership with Geoscience Australia,
publicly accessible, no API key required, CC-BY 4.0 licensed.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging

import aiohttp

from .const import ABS_TIMEOUT_S, ABS_URL, ABS_USER_AGENT

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AbsResult:
    """Fields extracted from the ABS Census G01 SA2 response."""

    sa2_code: str | None
    sa2_name: str | None
    population: int | None
    area_km2: float | None
    population_density: float | None  # persons per km²
    raw_attributes: dict | None


async def lookup_sa2_data(
    session: aiohttp.ClientSession,
    latitude: float,
    longitude: float,
) -> AbsResult | None:
    """Look up SA2-level census data for a coordinate.

    Returns None on any failure — caller decides whether to retain
    previous data or null out the sensors.
    """
    params = {
        # ArcGIS expects x,y = longitude,latitude
        "geometry": f"{longitude},{latitude}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",  # WGS84 — GPS native
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "sa2_code_2021,sa2_name_2021,tot_p_p,area_albers_sqkm",
        "returnGeometry": "false",
        "f": "json",
    }
    headers = {"User-Agent": ABS_USER_AGENT}

    try:
        async with asyncio.timeout(ABS_TIMEOUT_S):
            async with session.get(
                ABS_URL, params=params, headers=headers
            ) as resp:
                if resp.status != 200:
                    _LOGGER.warning(
                        "ABS returned HTTP %s for %f,%f",
                        resp.status, latitude, longitude,
                    )
                    return None
                data = await resp.json()
    except (aiohttp.ClientError, TimeoutError) as exc:
        _LOGGER.warning("ABS request failed: %s", exc)
        return None

    features = data.get("features") if isinstance(data, dict) else None
    if not features:
        # Empty result — point likely outside AU, or SA2 boundary gap
        return None

    attrs = features[0].get("attributes", {}) or {}

    sa2_code = attrs.get("sa2_code_2021")
    sa2_name = attrs.get("sa2_name_2021")
    population = attrs.get("tot_p_p")
    area = attrs.get("area_albers_sqkm")

    if not sa2_code:
        return None

    # Density: persons per km². Both inputs must be non-null and area non-zero.
    density: float | None = None
    if population is not None and area:
        try:
            density = round(float(population) / float(area), 2)
        except (ValueError, ZeroDivisionError, TypeError):
            density = None

    return AbsResult(
        sa2_code=str(sa2_code),
        sa2_name=str(sa2_name) if sa2_name is not None else None,
        population=int(population) if population is not None else None,
        area_km2=round(float(area), 2) if area is not None else None,
        population_density=density,
        raw_attributes=attrs,
    )
