# Clever Caravan Location

Home Assistant integration that tracks caravan/RV/van location, speed, and
GPS health. Built for mobile HA installs where the host moves with the
vehicle.

## Sources

- **USB GPS dongle** plugged into the HA host (default)
- **Entity-based** — read from existing HA entities (Starlink, device_tracker, etc.)
- **Manual** — input_number helpers for testing

## Sensors

Latitude, Longitude, Elevation, Speed, Status (Moving/Stationary/Parked),
GPS fix quality, satellites used/visible, HDOP, GPS healthy (binary).

## Roadmap

- v0.2: zone.home update, system timezone update, reverse-geocoding
- v0.3: MQTT source for off-host GPS

## Installation

HACS → ⋮ → Custom repositories →
`https://github.com/sambarlick/clever_caravan_location`
Type: Integration → Add. Restart HA. Settings → Devices & Services →
Add Integration → Clever Caravan Location.

## Companion

[Clever Caravan Weather](https://github.com/sambarlick/clever_caravan_integrations) — caravan-following BoM weather.
