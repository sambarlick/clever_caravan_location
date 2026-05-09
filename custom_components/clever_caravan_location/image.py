"""Image platform: serves the Wikipedia thumbnail via HA's image proxy.

This avoids writing files to /config/www/ — HA caches and serves the
remote image directly. Dashboard markdown can reference the image
entity via /api/image_proxy/image.clever_caravan_image.
"""

from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SIGNAL_WIKI_UPDATED
from .coordinator import CaravanLocationCoordinator, get_coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = get_coordinator(hass, entry.entry_id)
    async_add_entities([CaravanWikipediaImage(hass, coordinator, entry)])


class CaravanWikipediaImage(ImageEntity):
    """Image entity backed by Wikipedia's thumbnail URL."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "wikipedia_image"
    _attr_content_type = "image/jpeg"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: CaravanLocationCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(hass)
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_wikipedia_image"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Clever Caravan",
            manufacturer="Clever Caravan",
            model="Location",
        )
        self._current_url: str | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_WIKI_UPDATED, self._handle_update
            )
        )
        # Initial population if we already have data
        self._refresh_url()

    @callback
    def _handle_update(self) -> None:
        self._refresh_url()
        self.async_write_ha_state()

    def _refresh_url(self) -> None:
        wiki = self.coordinator.wiki_data
        new_url = wiki.image_url if wiki else None
        if new_url != self._current_url:
            self._current_url = new_url
            self._attr_image_url = new_url
            self._attr_image_last_updated = dt_util.utcnow()

    @property
    def available(self) -> bool:
        return self._current_url is not None
