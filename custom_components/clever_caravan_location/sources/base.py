"""Base class for location sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Callable

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LocationFix:
    """Normalised location fix from any source.

    Core fields are required. GPS-specific fields default to None so
    sources that don't have them (entity, manual) just leave them off.
    """

    latitude: float
    longitude: float
    elevation: float | None
    speed_kmh: float | None
    timestamp: datetime
    valid: bool
    # Optional GPS-specific signal — populated by USB source, not others
    fix_quality: int | None = None      # 0=no fix, 1=GPS, 2=DGPS, 4=RTK fix, 5=RTK float
    satellites_used: int | None = None
    satellites_visible: int | None = None
    hdop: float | None = None


class LocationSource(ABC):
    """Adapter contract."""

    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        self.hass = hass
        self.config = config
        self._listener: Callable[[LocationFix], None] | None = None
        self._unsub: Callable[[], None] | None = None
        self._latest: LocationFix | None = None

    @property
    def latest(self) -> LocationFix | None:
        return self._latest

    def subscribe(self, listener: Callable[[LocationFix], None]) -> None:
        self._listener = listener

    @abstractmethod
    async def async_start(self) -> None:
        """Begin listening to the underlying source."""

    async def async_stop(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    def _publish(self, fix: LocationFix) -> None:
        self._latest = fix
        if self._listener is not None:
            try:
                self._listener(fix)
            except Exception:  # noqa: BLE001
                _LOGGER.exception(
                    "Listener raised on fix from %s", type(self).__name__
                )
