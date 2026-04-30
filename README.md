# 🚐 Clever Caravan Location for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/sambarlick/clever_caravan_location.svg?style=for-the-badge)](https://github.com/sambarlick/clever_caravan_location/releases)
[![License](https://img.shields.io/github/license/sambarlick/clever_caravan_location.svg?style=for-the-badge)](LICENSE)
![Maintenance](https://img.shields.io/maintenance/yes/2026?style=for-the-badge)

A smart, logic-gated GPS tracking integration designed specifically for caravans, RVs, and mobile homelabs. 

---

## ✨ Features
* **Anti-Jitter Parked Snapshots:** Freezes coordinates and elevation when stationary to prevent database pollution.
* **Granular Reverse Geocoding:** Australia-aware cascading resolution (Suburb > Town > City).
* **Cold-Boot Safety:** Waits for the first live GPS ping to seed location; never restores stale data.

---

## 📥 Installation via HACS
1. Add `https://github.com/sambarlick/clever_caravan_location` as a Custom Repository.
2. Install and restart Home Assistant.
