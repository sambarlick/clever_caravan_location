"""USB GPS source.

Reads NMEA 0183 sentences from a USB GPS dongle via serial connection.
Self-contained — no gpsd, no add-on, no external broker. Works on HAOS.

Parses two NMEA sentence types:
- GGA: position, fix quality, satellites used, HDOP, altitude
- RMC: position, speed, validity flag

Auto-reconnects on dongle unplug/replug. Emits a LocationFix per
parsed sentence with valid data; coordinator does the throttling.
"""

from __future__ import annotations

import asyncio
import logging

import pynmea2
import serial_asyncio

from homeassistant.util import dt as dt_util

from ..const import (
    CONF_USB_BAUDRATE,
    CONF_USB_DEVICE,
    DEFAULT_BAUDRATE,
    LAT_MAX,
    LAT_MIN,
    LON_MAX,
    LON_MIN,
)
from .base import LocationFix, LocationSource

_LOGGER = logging.getLogger(__name__)

_RECONNECT_DELAY_S = 5
_KNOTS_TO_KMH = 1.852


class UsbSource(LocationSource):
    """Reads NMEA from a USB GPS dongle."""

    def __init__(self, hass, config) -> None:
        super().__init__(hass, config)
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        # Aggregated state — different NMEA sentences carry different fields,
        # so we accumulate and emit on each parsed sentence with valid data.
        self._lat: float | None = None
        self._lon: float | None = None
        self._alt: float | None = None
        self._speed_kmh: float | None = None
        self._fix_quality: int = 0
        self._sats_used: int = 0
        self._sats_visible: int = 0
        self._hdop: float | None = None
        self._has_fix = False

    async def async_start(self) -> None:
        self._stop_event.clear()
        self._task = asyncio.create_task(self._read_loop())

    async def async_stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._task = None

    async def _read_loop(self) -> None:
        """Outer loop: handles connect, disconnect, retry."""
        device = self.config[CONF_USB_DEVICE]
        baudrate = int(self.config.get(CONF_USB_BAUDRATE, DEFAULT_BAUDRATE))

        while not self._stop_event.is_set():
            try:
                _LOGGER.info("Connecting to GPS at %s @ %d baud", device, baudrate)
                reader, writer = await serial_asyncio.open_serial_connection(
                    url=device, baudrate=baudrate
                )
                _LOGGER.info("GPS connected")
                try:
                    await self._read_sentences(reader)
                finally:
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except Exception:  # noqa: BLE001
                        pass
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning(
                    "GPS read error (%s); retrying in %ds",
                    exc, _RECONNECT_DELAY_S,
                )

            # Wait before retry, but bail early if we're being stopped
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=_RECONNECT_DELAY_S
                )
            except asyncio.TimeoutError:
                pass

    async def _read_sentences(self, reader: asyncio.StreamReader) -> None:
        """Inner loop: read lines, parse NMEA, dispatch to handlers."""
        while not self._stop_event.is_set():
            try:
                line_bytes = await reader.readline()
            except Exception as exc:  # noqa: BLE001
                raise ConnectionError(f"Serial read failed: {exc}") from exc

            if not line_bytes:
                # EOF — typically dongle unplugged
                raise ConnectionError("EOF on serial port (dongle unplugged?)")

            line = line_bytes.decode("ascii", errors="replace").strip()
            if not line.startswith("$"):
                continue

            try:
                msg = pynmea2.parse(line)
            except pynmea2.ParseError:
                continue  # malformed sentence — ignore

            sentence_type = type(msg).__name__
            if sentence_type == "GGA":
                self._handle_gga(msg)
            elif sentence_type == "RMC":
                self._handle_rmc(msg)
            elif sentence_type == "GSV":
                self._handle_gsv(msg)
            # Other sentence types (GLL, VTG, GSA) are ignored — GGA + RMC
            # cover everything we care about.

    def _handle_gga(self, msg) -> None:
        try:
            if msg.gps_qual is not None:
                self._fix_quality = int(msg.gps_qual)
            if msg.latitude:
                self._lat = float(msg.latitude)
            if msg.longitude:
                self._lon = float(msg.longitude)
            if msg.num_sats:
                self._sats_used = int(msg.num_sats)
            if msg.horizontal_dil:
                self._hdop = float(msg.horizontal_dil)
            if msg.altitude is not None:
                self._alt = float(msg.altitude)
            self._has_fix = self._fix_quality > 0
            self._emit()
        except (ValueError, TypeError) as exc:
            _LOGGER.debug("Bad GGA sentence: %s", exc)

    def _handle_rmc(self, msg) -> None:
        try:
            if msg.status != "A":  # 'A' = active/valid, 'V' = void/warning
                return
            if msg.latitude:
                self._lat = float(msg.latitude)
            if msg.longitude:
                self._lon = float(msg.longitude)
            if msg.spd_over_grnd is not None:
                self._speed_kmh = float(msg.spd_over_grnd) * _KNOTS_TO_KMH
            self._has_fix = True
            self._emit()
        except (ValueError, TypeError) as exc:
            _LOGGER.debug("Bad RMC sentence: %s", exc)

    def _handle_gsv(self, msg) -> None:
        try:
            if msg.num_sv_in_view:
                self._sats_visible = int(msg.num_sv_in_view)
        except (ValueError, TypeError):
            pass

    def _emit(self) -> None:
        if not self._has_fix or self._lat is None or self._lon is None:
            return

        valid = (
            LAT_MIN <= self._lat <= LAT_MAX
            and LON_MIN <= self._lon <= LON_MAX
            and not (self._lat == 0.0 and self._lon == 0.0)  # Null Island
            and self._fix_quality > 0
        )

        self._publish(LocationFix(
            latitude=self._lat,
            longitude=self._lon,
            elevation=self._alt,
            speed_kmh=self._speed_kmh,
            timestamp=dt_util.utcnow(),
            valid=valid,
            fix_quality=self._fix_quality,
            satellites_used=self._sats_used,
            satellites_visible=self._sats_visible,
            hdop=self._hdop,
        ))
