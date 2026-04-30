# 🚐 Clever Caravan Location for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/sambarlick/clever_caravan_location.svg?style=for-the-badge)](https://github.com/sambarlick/clever_caravan_location/releases)
[![License](https://img.shields.io/github/license/sambarlick/clever_caravan_location.svg?style=for-the-badge)](LICENSE)
![Maintenance](https://img.shields.io/maintenance/yes/2026?style=for-the-badge)

A smart, logic-gated GPS tracking integration designed specifically for caravans, RVs, and mobile homelabs (like a Victron Cerbo GX payload). 

Unlike standard GPS trackers that continuously spam Home Assistant with coordinate jitter while parked, this integration uses an intelligent "Action Layer" to freeze updates, preserve database health, and smartly manage reverse-geocoding.

---

## ✨ Features

* **Anti-Jitter Parked Snapshots:** When the caravan stops moving, the integration takes a snapshot of the exact coordinates and freezes the latitude/longitude display sensors. This prevents GPS drift from polluting your Home Assistant recorder, history graphs, and UI.
* **Granular Reverse Geocoding:** Uses OSM Nominatim to resolve location data, featuring an Australia-aware cascading fallback that prioritizes Suburb/Town level granularity over generic City data.
* **Smart Action Gating:** Nominatim API calls, `zone.home` updates, and system timezone changes are strictly halted while parked to prevent API rate-limiting and unnecessary system calls.
* **Cold-Boot Safety:** Intentionally waits for the *first live GPS ping* after a Home Assistant reboot to seed its location data. It will never restore a stale database value, ensuring HA doesn't display a false location if the caravan was moved while the server was offline.
* **Rich Telemetry:** Exposes comprehensive sensors including Speed, Heading, Bearing, Climb Rate (m/s), Elevation, and GPS Atomic Time (forced UTC).

---

## 📥 Installation via HACS

This integration is installed as a Custom Repository in the Home Assistant Community Store (HACS).

1. Open **HACS** in Home Assistant.
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Add your repository URL: `https://github.com/sambarlick/clever_caravan_location`
4. Select **Integration** as the category and click **Add**.
5. Click on **Clever Caravan Location** in the HACS UI and click **Download**.
6. Restart Home Assistant.
7. Navigate to **Settings > Devices & Services > Add Integration** and search for "Clever Caravan Location".

---

## 📡 Sensor Overview

| Sensor | Description |
|--------|-------------|
| **Status** | Driving, Not Driving, or Parked Up. |
| **Latitude / Longitude** | Snapshotted when parked to prevent jitter. |
| **Caravan City** | Cascaded suburb/town resolution. |
| **Climb Rate & Gradient** | Calculated m/s based on a rolling elevation buffer. |
| **GPS Atomic Time** | Unformatted UTC string directly from the satellites. |
| **Accuracy** | Horizontal and Vertical DOP to meters. |

---

## Links

- **Repository:** [github.com/sambarlick/clever_caravan_location](https://github.com/sambarlick/clever_caravan_location)
- **Issues:** [github.com/sambarlick/clever_caravan_location/issues](https://github.com/sambarlick/clever_caravan_location/issues)

---

*Part of the [Clever Caravan](https://github.com/sambarlick) project · Built for mobile Home Assistant instances.*
