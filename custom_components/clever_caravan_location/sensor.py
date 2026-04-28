"""Sensor entities for Clever Caravan Location."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    UnitOfLength,
    UnitOfSpeed,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_LOCATION_UPDATED
from .coordinator import CaravanLocationCoordinator, get_coordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class CaravanSensorDescription(SensorEntityDescription):
    """Sensor description with a value getter against the coordinator."""

    value_fn: Callable[[CaravanLocationCoordinator], object]


SENSORS: tuple[CaravanSensorDescription, ...] = (
    CaravanSensorDescription(
        key="latitude",
        translation_key="latitude",
        icon="mdi:latitude",
        suggested_display_precision=6,
        value_fn=lambda c: c.latest.latitude if c.latest else None,
    ),
    CaravanSensorDescription(
        key="longitude",
        translation_key="longitude",
        icon="mdi:longitude",
        suggested_display_precision=6,
        value_fn=lambda c: c.latest.longitude if c.latest else None,
    ),
    CaravanSensorDescription(
        key="elevation",
        translation_key="elevation",
        icon="mdi:elevation-rise",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda c: c.latest.elevation if c.latest else None,
    ),
    CaravanSensorDescription(
        key="speed",
        translation_key="speed",
        icon="mdi:speedometer",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda c: c.latest.speed_kmh if c.latest else None,
    ),
    CaravanSensorDescription(
        key="status",
        translation_key="status",
        icon="mdi:caravan",
        value_fn=lambda c: c.status,
    ),
    CaravanSensorDescription(
        key="fix_quality",
        translation_key="fix_quality",
        icon="mdi:crosshairs-gps",
        value_fn=lambda c: c.latest.fix_quality if c.latest else None,
    ),
    CaravanSensorDescription(
        key="satellites_used",
        translation_key="satellites_used",
        icon="mdi:satellite-uplink",
        native_unit_of_measurement="sat",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda c: c.latest.satellites_used if c.latest else None,
    ),
    CaravanSensorDescription(
        key="satellites_visible",
        translation_key="satellites_visible",
        icon="mdi:satellite-variant",
        native_unit_of_measurement="sat",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda c: c.latest.satellites_visible if c.latest else None,
    ),
    CaravanSensorDescription(
        key="hdop",
        translation_key="hdop",
        icon="mdi:target",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda c: c.latest.hdop if c.latest else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities for this config entry."""
    coordinator = get_coordinator(hass, entry.entry_id)
    async_add_entities(
        CaravanSensor(coordinator, entry, desc) for desc in SENSORS
    )


class CaravanSensor(SensorEntity):
    """Generic caravan sensor reading from the coordinator."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    entity_description: CaravanSensorDescription

    def __init__(
        self,
        coordinator: CaravanLocationCoordinator,
        entry: ConfigEntry,
        description: CaravanSensorDescription,
    ) -> None:
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Clever Caravan",
            manufacturer="Clever Caravan",
            model="Location",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_LOCATION_UPDATED, self._handle_update
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator)

    @property
    def available(self) -> bool:
        # status sensor stays available even when there's no fix yet
        # (it shows "Unknown") so the dashboard isn't blank on first boot.
        if self.entity_description.key == "status":
            return True
        return self.coordinator.latest is not None
