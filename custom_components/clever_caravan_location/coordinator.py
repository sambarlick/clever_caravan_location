"""Coordinator: canonical state + action layer.

Subscribes to a single source adapter. Two responsibilities:

1. Read side: derive caravan status, expose latest fix to sensors.
2. Action side: when the fix changes meaningfully, update HA core
   state — zone.home location, system timezone, reverse-geocode.

Each action throttles independently — different geographic deltas
matter for different things. set_location reacts to caravan-scale
movement. Timezone updates only when crossing state-border-scale
distances. Nominatim respects the public rate-limit policy.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging

import aiohttp

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    GEOCODE_MIN_DELTA_DEG,
    GEOCODE_MIN_INTERVAL_S,
    PARKED_AFTER_MINUTES,
    SET_LOCATION_MIN_DELTA_DEG,
    SIGNAL_GEOCODE_UPDATED,
    SIGNAL_LOCATION_UPDATED,
    SPEED_MOVING_THRESHOLD,
    SPEED_STATIONARY_THRESHOLD,
    STATUS_MOVING,
    STATUS_PARKED,
    STATUS_STATIONARY,
    STATUS_UNKNOWN,
    TIMEZONE_MIN_DELTA_DEG,
)
from .nominatim import GeocodeResult, reverse_geocode
from .sources import LocationFix, LocationSource

_LOGGER = logging.getLogger(__name__)


class CaravanLocationCoordinator:
    """Single source of truth for caravan location state and actions."""

    def __init__(self, hass: HomeAssistant, source: LocationSource) -> None:
        self.hass = hass
        self.source = source

        # Read state
        self._latest: LocationFix | None = None
        self._status: str = STATUS_UNKNOWN
        self._last_movement: datetime | None = None
        self._geocode: GeocodeResult | None = None

        # Action throttles — track last-fired position for each action
        self._last_set_location: tuple[float, float] | None = None
        self._last_timezone: tuple[float, float] | None = None
        self._last_geocode_at: datetime | None = None
        self._last_geocode_pos: tuple[float, float] | None = None

        # timezonefinder is created lazily — it loads ~50MB of polygon
        # data and we don't want that on the import path.
        self._tz_finder = None
        self._tz_finder_lock = asyncio.Lock()

        source.subscribe(self._on_fix)

    # --- Public read API ---

    @property
    def latest(self) -> LocationFix | None:
        return self._latest

    @property
    def status(self) -> str:
        return self._status

    @property
    def is_healthy(self) -> bool:
        if self._latest is None:
            return False
        age = (dt_util.utcnow() - self._latest.timestamp).total_seconds()
        return self._latest.valid and age < 600

    @property
    def geocode(self) -> GeocodeResult | None:
        return self._geocode

    # --- Public action API (called by service handler) ---

    async def async_force_update(self) -> None:
        """Force all action paths to fire on the latest fix.

        Bypasses throttles. Used by the service entry point so the
        user can trigger an explicit refresh from automations or UI.
        """
        if self._latest is None or not self._latest.valid:
            _LOGGER.warning("Cannot force update: no valid fix yet")
            return
        fix = self._latest
        await self._update_zone_home(fix, force=True)
        await self._update_timezone(fix, force=True)
        await self._update_geocode(fix, force=True)

    # --- Internal: fix dispatch ---

    @callback
    def _on_fix(self, fix: LocationFix) -> None:
        self._latest = fix
        self._update_status(fix)
        async_dispatcher_send(self.hass, SIGNAL_LOCATION_UPDATED)

        # Action layer fires async; don't block the source callback.
        if fix.valid:
            self.hass.async_create_task(self._run_actions(fix))

    async def _run_actions(self, fix: LocationFix) -> None:
        """Action layer: each action throttles independently."""
        await self._update_zone_home(fix)
        await self._update_timezone(fix)
        await self._update_geocode(fix)

    # --- Status derivation (unchanged from v0.1) ---

    def _update_status(self, fix: LocationFix) -> None:
        if not fix.valid:
            self._status = STATUS_UNKNOWN
            return

        speed = fix.speed_kmh
        now = fix.timestamp

        if speed is None:
            self._status = STATUS_STATIONARY
            return

        if speed >= SPEED_MOVING_THRESHOLD:
            self._status = STATUS_MOVING
            self._last_movement = now
            return

        if speed >= SPEED_STATIONARY_THRESHOLD:
            self._status = STATUS_STATIONARY
            return

        if self._last_movement is None:
            self._last_movement = now
            self._status = STATUS_STATIONARY
            return

        dwell = now - self._last_movement
        if dwell >= timedelta(minutes=PARKED_AFTER_MINUTES):
            self._status = STATUS_PARKED
        else:
            self._status = STATUS_STATIONARY

    # --- Action: zone.home ---

    async def _update_zone_home(
        self, fix: LocationFix, force: bool = False
    ) -> None:
        if not force and not self._delta_exceeds(
            self._last_set_location, fix, SET_LOCATION_MIN_DELTA_DEG
        ):
            return

        try:
            await self.hass.services.async_call(
                "homeassistant",
                "set_location",
                {
                    "latitude": fix.latitude,
                    "longitude": fix.longitude,
                    **(
                        {"elevation": int(fix.elevation)}
                        if fix.elevation is not None
                        else {}
                    ),
                },
                blocking=False,
            )
            self._last_set_location = (fix.latitude, fix.longitude)
            _LOGGER.debug(
                "zone.home updated to %.5f, %.5f",
                fix.latitude, fix.longitude,
            )
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Failed to update zone.home")

    # --- Action: timezone ---

    async def _ensure_tz_finder(self):
        """Lazy-init timezonefinder on first use."""
        if self._tz_finder is not None:
            return self._tz_finder
        async with self._tz_finder_lock:
            if self._tz_finder is None:
                from timezonefinder import TimezoneFinder
                self._tz_finder = await self.hass.async_add_executor_job(
                    TimezoneFinder
                )
        return self._tz_finder

    async def _update_timezone(
        self, fix: LocationFix, force: bool = False
    ) -> None:
        if not force and not self._delta_exceeds(
            self._last_timezone, fix, TIMEZONE_MIN_DELTA_DEG
        ):
            return

        try:
            tf = await self._ensure_tz_finder()
            tz_name = await self.hass.async_add_executor_job(
                tf.timezone_at, lng=fix.longitude, lat=fix.latitude,
            )
            if tz_name and tz_name != self.hass.config.time_zone:
                await self.hass.config.async_set_time_zone(tz_name)
                _LOGGER.info("System timezone updated to %s", tz_name)
            self._last_timezone = (fix.latitude, fix.longitude)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Failed to update system timezone")

    # --- Action: reverse-geocode ---

    async def _update_geocode(
        self, fix: LocationFix, force: bool = False
    ) -> None:
        now = dt_util.utcnow()

        if not force:
            # Two throttles: distance AND time. Need to fail both to skip.
            time_ok = (
                self._last_geocode_at is None
                or (now - self._last_geocode_at).total_seconds()
                   >= GEOCODE_MIN_INTERVAL_S
            )
            dist_ok = self._delta_exceeds(
                self._last_geocode_pos, fix, GEOCODE_MIN_DELTA_DEG
            )
            if not (time_ok and dist_ok):
                return

        session = async_get_clientsession(self.hass)
        result = await reverse_geocode(
            session, fix.latitude, fix.longitude,
        )

        # Update bookkeeping even on failure — don't hammer the API
        # retrying the same coordinates.
        self._last_geocode_at = now
        self._last_geocode_pos = (fix.latitude, fix.longitude)

        if result is not None:
            self._geocode = result
            async_dispatcher_send(self.hass, SIGNAL_GEOCODE_UPDATED)
            _LOGGER.debug(
                "Geocode: %s, %s, %s",
                result.city, result.state, result.country,
            )

    # --- Helpers ---

    @staticmethod
    def _delta_exceeds(
        last: tuple[float, float] | None,
        fix: LocationFix,
        threshold_deg: float,
    ) -> bool:
        """True if the fix is far enough from `last` to fire an action.

        Cheap chebyshev distance — exact great-circle isn't needed at
        these scales. Threshold values in const.py document the
        approximate metres-per-degree at typical Australian latitudes.
        """
        if last is None:
            return True
        return (
            abs(fix.latitude - last[0]) >= threshold_deg
            or abs(fix.longitude - last[1]) >= threshold_deg
        )


def get_coordinator(hass: HomeAssistant, entry_id: str) -> CaravanLocationCoordinator:
    return hass.data[DOMAIN][entry_id]["coordinator"]
