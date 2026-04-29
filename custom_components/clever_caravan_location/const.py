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

# Status enum values (Sam's terms)
STATUS_DRIVING = "Driving"
STATUS_NOT_DRIVING = "Not Driving"
STATUS_PARKED_UP = "Parked Up"
STATUS_UNKNOWN = None  # HA-native unknown state (no valid fix yet)

STATUS_OPTIONS = [STATUS_DRIVING, STATUS_NOT_DRIVING, STATUS_PARKED_UP]

# Fix quality enum (NMEA $GPGGA field 7) → user-facing accuracy labels
FIX_QUALITY_LABELS: dict[int, str] = {
    0: "No Signal",
    1: "Standard (~3-5m accuracy)",
    2: "Standard (~1m accuracy)",
    4: "High Precision (~1cm accuracy)",
    5: "High Precision (~10cm accuracy)",
    6: "Estimated (predicted from last movement)",
    9: "Enhanced (~1m accuracy)",
}
FIX_QUALITY_OPTIONS = list(FIX_QUALITY_LABELS.values())

# Fix mode enum (NMEA $GPGSA field 2)
FIX_MODE_NO_FIX = "No Fix"
FIX_MODE_2D = "2D Fix"
FIX_MODE_3D = "3D Fix"
FIX_MODE_OPTIONS = [FIX_MODE_NO_FIX, FIX_MODE_2D, FIX_MODE_3D]

# Gradient enum
GRADIENT_CLIMBING = "Climbing"
GRADIENT_DESCENDING = "Descending"
GRADIENT_LEVEL = "Level"
GRADIENT_OPTIONS = [GRADIENT_CLIMBING, GRADIENT_LEVEL, GRADIENT_DESCENDING]

# Heading: 16-direction compass rose (matches the old MQTT add-on)
HEADING_DIRECTIONS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]

# Speed thresholds (km/h)
SPEED_DRIVING_THRESHOLD = 5.0
SPEED_NOT_DRIVING_THRESHOLD = 1.0
PARKED_UP_AFTER_MINUTES = 20

# Climb thresholds (m/s) — gradient classifier
CLIMB_GRADIENT_THRESHOLD_MS = 0.5
# Window over which to compute climb rate from elevation samples
CLIMB_WINDOW_S = 5.0

# USB defaults
DEFAULT_BAUDRATE = 9600

# DOP-to-accuracy multiplier (rule of thumb: ~5m baseline × DOP)
DOP_TO_METRES = 5.0

# Sanity bounds
LAT_MIN = -90.0
LAT_MAX = 90.0
LON_MIN = -180.0
LON_MAX = 180.0

# Action layer thresholds
SET_LOCATION_MIN_DELTA_DEG = 0.001        # ~110m
TIMEZONE_MIN_DELTA_DEG = 0.1              # ~11km
GEOCODE_MIN_DELTA_DEG = 0.01              # ~1.1km
GEOCODE_MIN_INTERVAL_S = 60

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
