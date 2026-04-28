"""Constants for Clever Caravan Location."""

from __future__ import annotations

DOMAIN = "clever_caravan_location"

# Config entry keys
CONF_SOURCE = "source"
CONF_LATITUDE_ENTITY = "latitude_entity"
CONF_LONGITUDE_ENTITY = "longitude_entity"
CONF_ELEVATION_ENTITY = "elevation_entity"
CONF_SPEED_ENTITY = "speed_entity"
CONF_USB_DEVICE = "usb_device"
CONF_USB_BAUDRATE = "usb_baudrate"

# Source types
SOURCE_USB = "usb"          # USB GPS dongle plugged into HA host (default, v0.2)
SOURCE_ENTITY = "entity"    # Starlink, iPad device_tracker, anything entity-based
SOURCE_MANUAL = "manual"    # input_number helpers, testing only
# v0.3 will add: SOURCE_MQTT (off-host GPS via Docker container)

SOURCES = [SOURCE_USB, SOURCE_ENTITY, SOURCE_MANUAL]

# Status values - single source of truth
STATUS_MOVING = "Moving"
STATUS_STATIONARY = "Stationary"
STATUS_PARKED = "Parked"
STATUS_UNKNOWN = "Unknown"

# Speed thresholds (km/h)
SPEED_MOVING_THRESHOLD = 5.0
SPEED_STATIONARY_THRESHOLD = 1.0
PARKED_AFTER_MINUTES = 20

# USB defaults
DEFAULT_BAUDRATE = 9600

# Sanity bounds
LAT_MIN = -90.0
LAT_MAX = 90.0
LON_MIN = -180.0
LON_MAX = 180.0

# Service
SERVICE_UPDATE = "update"

# Signal dispatch
SIGNAL_LOCATION_UPDATED = f"{DOMAIN}_location_updated"
