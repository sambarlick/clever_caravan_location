"""Coordinator: canonical state + action layer."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import (
    CLIMB_GRADIENT_THRESHOLD_MS,
    CLIMB_WINDOW_S,
    DOMAIN,
    GEOCODE_MIN_DELTA_DEG,
    GEOCODE_MIN_INTERVAL_S,
    GRADIENT_CLIMBING,
    GRADIENT_DESCENDING,
    GRADIENT_LEVEL,
    PARKED_UP_AFTER_MINUTES,
    SET_LOCATION_MIN_DELTA_DEG,
    SIGNAL_GEOCODE_UPDATED,
    SIGNAL_LOCATION_UPDATED,
    SPEED_DRIVING_THRESHOLD,
    SPEED_NOT_DRIVING_THRESHOLD,
    STATUS_DRIVING,
    STATUS_NOT_DRIVING,
    STATUS_PARKED_UP,
    STATUS_UNKNOWN,
    TIMEZONE_MIN_DELTA_DEG,
)
from .nominatim import GeocodeResult, reverse_geocode
from .sources import LocationFix, LocationSource

_LOGGER = logging.getLogger(__name__)

class CaravanLocationCoordinator:
    def __init__(self, hass: HomeAssistant, source: LocationSource) -> None:
        self.hass = hass
        self.source = source

        self._latest: LocationFix | None = None
        self._status: str | None = STATUS_UNKNOWN
        self._previous_status: str | None = STATUS_UNKNOWN
        self._last_movement: datetime | None = None
        self._geocode: GeocodeResult | None = None

        self._elev_buffer: deque[tuple[datetime, float]] = deque()
        self._climb_ms: float | None = None

        # Dejitter snapshots (mirrors gpsd2mqtt.py startup_override & parked logic)
        self._snapshot_lat: float | None = None
        self._snapshot_lon: float | None = None

        # Action layer gating
        self._cold_start_bootstrap_pending = True
        self._last_set_location: tuple[float, float] | None = None
        self._last_timezone: tuple[float, float] | None = None
        self._last_geocode_at: datetime | None = None
        self._last_geocode_pos: tuple[float, float] | None = None

        source.subscribe(self._on_fix)

    @property
    def latest(self) -> LocationFix | None:
        return self._latest

    @property
    def status(self) -> str | None:
        return self._status

    @property
    def display_latitude(self) -> float | None:
        if self._status == STATUS_DRIVING:
            return self._latest.latitude if self._latest else None
        return self._snapshot_lat

    @property
    def display_longitude(self) -> float | None:
        if self._status == STATUS_DRIVING:
            return self._latest.longitude if self._latest else None
        return self._snapshot_lon

    @property
    def display_speed(self) -> float | None:
        # Matches gpsd2mqtt.py: forces 0.0 when parked to hide jitter
        if self._status == STATUS_DRIVING:
            return self._latest.speed_kmh if self._latest else None
        return 0.0

    @property
    def climb_ms(self) -> float | None:
        return self._climb_ms

    @property
    def gradient(self) -> str | None:
        if self._climb_ms is None:
            return None
        if self._climb_ms > CLIMB_GRADIENT_THRESHOLD_MS:
            return GRADIENT_CLIMBING
        if self._climb_ms < -CLIMB_GRADIENT_THRESHOLD_MS:
            return GRADIENT_DESCENDING
        return GRADIENT_LEVEL

    @property
    def is_healthy(self) -> bool:
        if self._latest is None:
            return False
        age = (dt_util.utcnow() - self._latest.timestamp).total_seconds()
        return self._latest.valid and age < 600

    @property
    def geocode(self) -> GeocodeResult | None:
        return self._geocode

    @callback
    def _on_fix(self, fix: LocationFix) -> None:
        self._latest = fix
        self._update_status(fix)
        self._update_climb(fix)
        self._update_snapshot(fix)
        async_dispatcher_send(self.hass, SIGNAL_LOCATION_UPDATED)

        if fix.valid and self._should_run_actions():
            self.hass.async_create_task(self._run_actions(fix))

        self._previous_status = self._status

    def _should_run_actions(self) -> bool:
        if self._cold_start_bootstrap_pending:
            self._cold_start_bootstrap_pending = False
            return True
        if self._status == STATUS_DRIVING:
            return True
        if self._previous_status == STATUS_DRIVING and self._status != STATUS_DRIVING:
            return True
        return False

    async def _run_actions(self, fix: LocationFix) -> None:
        await self._update_zone_home(fix)
        await self._update_timezone(fix)
        await self._update_geocode(fix)

    def _update_status(self, fix: LocationFix) -> None:
        if not fix.valid:
            self._status = STATUS_UNKNOWN
            return

        speed = fix.speed_kmh
        now = fix.timestamp

        if speed is None:
            self._status = STATUS_NOT_DRIVING
            return

        if speed >= SPEED_DRIVING_THRESHOLD:
            self._status = STATUS_DRIVING
            self._last_movement = now
            return

        if speed >= SPEED_NOT_DRIVING_THRESHOLD:
            self._status = STATUS_NOT_DRIVING
            return

        if self._last_movement is None:
            self._last_movement = now
            self._status = STATUS_NOT_DRIVING
            return

        dwell = now - self._last_movement
        if dwell >= timedelta(minutes=PARKED_UP_AFTER_MINUTES):
            self._status = STATUS_PARKED_UP
        else:
            self._status = STATUS_NOT_DRIVING

    def _update_snapshot(self, fix: LocationFix) -> None:
        if not fix.valid:
            return
        # Matches gpsd2mqtt.py: updates if moving OR if snapshot is empty (startup_override)
        if self._status == STATUS_DRIVING or self._snapshot_lat is None:
            self._snapshot_lat = fix.latitude
            self._snapshot_lon = fix.longitude

    def _update_climb(self, fix: LocationFix) -> None:
        if not fix.valid or fix.elevation is None:
            return
        now = fix.timestamp
        self._elev_buffer.append((now, fix.elevation))
        cutoff = now - timedelta(seconds=CLIMB_WINDOW_S)
        while self._elev_buffer and self._elev_buffer[0][0] < cutoff:
            self._elev_buffer.popleft()
        if len(self._elev_buffer) < 2:
            self._climb_ms = None
            return
        oldest_t, oldest_e = self._elev_buffer[0]
        dt = (now - oldest_t).total_seconds()
        if dt <= 0:
            return
        self._climb_ms = (fix.elevation - oldest_e) / dt

    async def _update_zone_home(self, fix: LocationFix, force: bool = False) -> None:
        if not force and not self._delta_exceeds(self._last_set_location, fix, SET_LOCATION_MIN_DELTA_DEG):
            return
        try:
            await self.hass.services.async_call(
                "homeassistant", "set_location",
                {
                    "latitude": fix.latitude,
                    "longitude": fix.longitude,
                    **({"elevation": int(fix.elevation)} if fix.elevation is not None else {}),
                },
                blocking=False,
            )
            self._last_set_location = (fix.latitude, fix.longitude)
        except Exception:
            pass

    async def _update_timezone(self, fix: LocationFix, force: bool = False) -> None:
        if not force and not self._delta_exceeds(self._last_timezone, fix, TIMEZONE_MIN_DELTA_DEG):
            return
        try:
            from tzfpy import get_tz
            tz_name = await self.hass.async_add_executor_job(get_tz, fix.longitude, fix.latitude)
            if tz_name and tz_name != self.hass.config.time_zone:
                await self.hass.config.async_set_time_zone(tz_name)
            self._last_timezone = (fix.latitude, fix.longitude)
        except Exception:
            pass

    async def _update_geocode(self, fix: LocationFix, force: bool = False) -> None:
        now = dt_util.utcnow()
        if not force:
            time_ok = (self._last_geocode_at is None or (now - self._last_geocode_at).total_seconds() >= GEOCODE_MIN_INTERVAL_S)
            dist_ok = self._delta_exceeds(self._last_geocode_pos, fix, GEOCODE_MIN_DELTA_DEG)
            if not (time_ok and dist_ok):
                return
        session = async_get_clientsession(self.hass)
        result = await reverse_geocode(session, fix.latitude, fix.longitude)
        self._last_geocode_at = now
        self._last_geocode_pos = (fix.latitude, fix.longitude)
        if result is not None:
            self._geocode = result
            async_dispatcher_send(self.hass, SIGNAL_GEOCODE_UPDATED)

    @staticmethod
    def _delta_exceeds(last: tuple[float, float] | None, fix: LocationFix, threshold_deg: float) -> bool:
        if last is None:
            return True
        return (abs(fix.latitude - last[0]) >= threshold_deg or abs(fix.longitude - last[1]) >= threshold_deg)

def get_coordinator(hass: HomeAssistant, entry_id: str) -> CaravanLocationCoordinator:
    return hass.data[DOMAIN][entry_id]["coordinator"]
