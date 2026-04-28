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
CONF_REVERSE_GEOCODE = "reverse_geocode"

# Source types
SOURCE_USB = "usb"
SOURCE_ENTITY = "entity"
SOURCE_MANUAL = "manual"
SOURCES = [SOURCE_USB, SOURCE_ENTITY, SOURCE_MANUAL]

# Status values
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

# --- Action layer thresholds ---
# Different actions throttle at different distances. The asymmetry
# is intentional: set_location is cheap and we want it responsive,
# timezone changes only matter at state-border scale, Nominatim
# costs API calls so we batch them.
SET_LOCATION_MIN_DELTA_DEG = 0.001        # ~110m  — caravan-scale movement
TIMEZONE_MIN_DELTA_DEG = 0.1              # ~11km  — only state crossings
GEOCODE_MIN_DELTA_DEG = 0.01              # ~1.1km — suburb-scale moves
GEOCODE_MIN_INTERVAL_S = 60               # respect Nominatim rate limit

# Nominatim
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_USER_AGENT = (
    "CleverCaravan/0.2 "
    "(https://github.com/sambarlick/clever_caravan_location)"
)
NOMINATIM_TIMEOUT_S = 10

# Service
SERVICE_UPDATE = "update"

# Signal dispatch
SIGNAL_LOCATION_UPDATED = f"{DOMAIN}_location_updated"
SIGNAL_GEOCODE_UPDATED = f"{DOMAIN}_geocode_updated"
