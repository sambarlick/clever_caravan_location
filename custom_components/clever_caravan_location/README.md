# Clever Caravan Location

Tracks caravan location, speed, and GPS health for mobile Home Assistant
installs. Built for caravan/RV/van use where the HA host moves with the
vehicle.

## v0.1.0 — data ingestion

- **USB GPS dongle** plugged into the HA host (default)
- **Entity-based** — read from existing HA entities (Starlink, device_tracker, etc.)
- **Manual** — input_number helpers for testing

Creates sensors for latitude, longitude, elevation, speed, status
(Moving/Stationary/Parked), GPS fix quality, satellite counts, HDOP, plus
a GPS-healthy binary sensor.

Does **not** update zone.home or system timezone — that's v0.2.

## Setup

Settings → Devices & Services → Add Integration → "Clever Caravan Location"
