"""Config flow for Clever Caravan Location."""

from __future__ import annotations

import os
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ELEVATION_ENTITY,
    CONF_LATITUDE_ENTITY,
    CONF_LONGITUDE_ENTITY,
    CONF_SOURCE,
    CONF_SPEED_ENTITY,
    CONF_USB_BAUDRATE,
    CONF_USB_DEVICE,
    DEFAULT_BAUDRATE,
    DOMAIN,
    SOURCE_ENTITY,
    SOURCE_MANUAL,
    SOURCE_USB,
    SOURCES,
)


def _scan_serial_devices() -> list[str]:
    """List USB serial devices by stable id.

    /dev/serial/by-id/* paths are stable across reboots and survive
    different USB ports — better than /dev/ttyACM0 which can change.
    """
    by_id = "/dev/serial/by-id"
    if not os.path.isdir(by_id):
        return []
    try:
        return sorted(
            os.path.join(by_id, name)
            for name in os.listdir(by_id)
        )
    except OSError:
        return []


class CleverCaravanLocationConfigFlow(ConfigFlow, domain=DOMAIN):
    """Two-step flow: pick source type, then pick source-specific config."""

    VERSION = 1

    def __init__(self) -> None:
        self._source_type: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        # Single instance only — two configs would fight over zone.home.
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            self._source_type = user_input[CONF_SOURCE]
            if self._source_type == SOURCE_USB:
                return await self.async_step_usb()
            return await self.async_step_entities()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_SOURCE, default=SOURCE_USB): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=SOURCES,
                        translation_key="source",
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }),
        )

    async def async_step_usb(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """USB GPS configuration: pick device + baudrate."""
        detected = await self.hass.async_add_executor_job(_scan_serial_devices)

        if user_input is not None:
            data = {
                CONF_SOURCE: SOURCE_USB,
                CONF_USB_DEVICE: user_input[CONF_USB_DEVICE],
                CONF_USB_BAUDRATE: int(user_input[CONF_USB_BAUDRATE]),
            }
            return self.async_create_entry(
                title="Clever Caravan (USB GPS)", data=data,
            )

        # custom_value=True lets the user type a path even when nothing's
        # auto-detected (e.g. dongle plugged in after onboarding starts).
        device_default = detected[0] if detected else ""

        return self.async_show_form(
            step_id="usb",
            data_schema=vol.Schema({
                vol.Required(CONF_USB_DEVICE, default=device_default): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=detected,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        custom_value=True,
                    )
                ),
                vol.Required(CONF_USB_BAUDRATE, default=DEFAULT_BAUDRATE): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=2400, max=921600, step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }),
        )

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Entity-based or manual source: pick the entities."""
        if user_input is not None:
            data = {CONF_SOURCE: self._source_type, **user_input}
            title = {
                SOURCE_ENTITY: "Clever Caravan (Entity-based)",
                SOURCE_MANUAL: "Clever Caravan (Manual)",
            }[self._source_type or SOURCE_ENTITY]
            return self.async_create_entry(title=title, data=data)

        sensor_or_input = selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "device_tracker"],
            )
        )

        return self.async_show_form(
            step_id="entities",
            data_schema=vol.Schema({
                vol.Required(CONF_LATITUDE_ENTITY): sensor_or_input,
                vol.Required(CONF_LONGITUDE_ENTITY): sensor_or_input,
                vol.Optional(CONF_ELEVATION_ENTITY): sensor_or_input,
                vol.Optional(CONF_SPEED_ENTITY): sensor_or_input,
            }),
            description_placeholders={"source": self._source_type or ""},
        )
