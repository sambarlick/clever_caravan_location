"""Coordinator: owns canonical caravan location state.

Subscribes to a single source adapter, derives caravan status
(Moving/Stationary/Parked) from the speed signal, and notifies sensors
when state changes.

Sensors read from this coordinator only — never from the source. That
guarantees one source of truth for status strings, units, and validity.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    PARKED_AFTER_MINUTES,
    SIGNAL_LOCATION_UPDATED,
    SPEED_MOVING_THRESHOLD,
    SPEED_STATIONARY_THRESHOLD,
    STATUS_MOVING,
    STATUS_PARKED,
    STATUS_STATIONARY,
    STATUS_UNKNOWN,
)
from .sources import LocationFix, LocationSource

_LOGGER = logging.getLogger(__name__)


class CaravanLocationCoordinator:
    """Single source of truth for caravan location state."""

    def __init__(self, hass: HomeAssistant, source: LocationSource) -> None:
        self.hass = hass
        self.source = source
        self._latest: LocationFix | None = None
        # When did we last see speed > stationary threshold? Used to
        # promote Stationary → Parked after PARKED_AFTER_MINUTES.
        self._last_movement: datetime | None = None
        self._status: str = STATUS_UNKNOWN
        source.subscribe(self._on_fix)

    # --- Public read API used by sensors ---

    @property
    def latest(self) -> LocationFix | None:
        return self._latest

    @property
    def status(self) -> str:
        return self._status

    @property
    def is_healthy(self) -> bool:
        """GPS health: a recent fix that's structurally valid."""
        if self._latest is None:
            return False
        age = (dt_util.utcnow() - self._latest.timestamp).total_seconds()
        return self._latest.valid and age < 600  # 10min freshness window

    # --- Internal: fix dispatch ---

    @callback
    def _on_fix(self, fix: LocationFix) -> None:
        """Called by the source whenever it has a new fix."""
        self._latest = fix
        self._update_status(fix)
        async_dispatcher_send(self.hass, SIGNAL_LOCATION_UPDATED)

    def _update_status(self, fix: LocationFix) -> None:
        """Derive Moving/Stationary/Parked from speed + dwell time."""
        if not fix.valid:
            self._status = STATUS_UNKNOWN
            return

        speed = fix.speed_kmh
        now = fix.timestamp

        if speed is None:
            # No speed signal (e.g. entity source without speed entity).
            # Best we can do is "Stationary if we've ever seen a fix".
            self._status = STATUS_STATIONARY
            return

        if speed >= SPEED_MOVING_THRESHOLD:
            self._status = STATUS_MOVING
            self._last_movement = now
            return

        if speed >= SPEED_STATIONARY_THRESHOLD:
            self._status = STATUS_STATIONARY
            return

        # Speed below stationary threshold. If we've been here long
        # enough, promote to Parked.
        if self._last_movement is None:
            self._last_movement = now  # first fix; treat as just-arrived
            self._status = STATUS_STATIONARY
            return

        dwell = now - self._last_movement
        if dwell >= timedelta(minutes=PARKED_AFTER_MINUTES):
            self._status = STATUS_PARKED
        else:
            self._status = STATUS_STATIONARY


def get_coordinator(hass: HomeAssistant, entry_id: str) -> CaravanLocationCoordinator:
    """Lookup helper for sensor platforms."""
    return hass.data[DOMAIN][entry_id]["coordinator"]
