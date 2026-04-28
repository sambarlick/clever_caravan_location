"""Clever Caravan Location integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, SERVICE_UPDATE
from .coordinator import CaravanLocationCoordinator
from .sources import build_source

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Clever Caravan Location from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    source = build_source(hass, dict(entry.data))
    coordinator = CaravanLocationCoordinator(hass, source)
    await source.async_start()

    hass.data[DOMAIN][entry.entry_id] = {
        "source": source,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Register the update service once (across all entries — single instance
    # is enforced in the config flow anyway).
    if not hass.services.has_service(DOMAIN, SERVICE_UPDATE):
        async def _handle_update(_call: ServiceCall) -> None:
            for data in hass.data[DOMAIN].values():
                if "coordinator" in data:
                    await data["coordinator"].async_force_update()

        hass.services.async_register(DOMAIN, SERVICE_UPDATE, _handle_update)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["source"].async_stop()
        # Last entry going? Tear down the service.
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_UPDATE)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
