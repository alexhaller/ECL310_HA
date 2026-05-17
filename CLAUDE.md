# CLAUDE.md — ECL310_HA

## Project overview

Custom Home Assistant integration for the Danfoss ECL 310 district heating controller. Communicates via Modbus TCP (default port 502, slave ID 1). The Modbus register map is fixed per the ECL 310 datasheet — do not change register addresses without verifying against the device documentation.

- GitHub: https://github.com/alexhaller/ECL310_HA

Key files:
- `custom_components/ecl310/ecl310.py` — device communication layer; all Modbus reads/writes; `async_update_slow()` and `async_update_fast()` read separate register subsets
- `custom_components/ecl310/__init__.py` — two coordinators (`slow_coordinator` 30 s fixed, `adaptive_coordinator` 30 s idle / configurable active), `BaseEntity`, `async_setup_entry`, `async_unload_entry`
- `custom_components/ecl310/config_flow.py` — required user inputs: host, port (default 502), slave_id (default 1); options: active_interval (default 5 s)
- `custom_components/ecl310/const.py` — DOMAIN, all register address constants, OPERATING_MODES mapping
- Platforms: `sensor.py` (21 sensors), `number.py` (4 setpoints), `select.py` (2 operating modes)

## Coordinator architecture

Two coordinators share a single `ECL310Device` instance (same TCP connection, shared properties):

| Coordinator | Poll interval | Registers | Entities |
|---|---|---|---|
| `slow_coordinator` | 30 s fixed | outside temp (10200), outside min/max, status (4210–4211), sonometer volume+energy (6011–6014) | `slow=True` sensors |
| `adaptive_coordinator` | 30 s idle → active when `sonometer_flow > 0` | circuit temps (10202–10205), op modes (4200–4201), setpoints (11179, 12189), sonometer live (6005–6010) | all other entities |

**Default is adaptive** — any new sensor/number/select entity uses `adaptive_coordinator` unless `slow=True` is set on its `ECL310SensorDescription`.

Active interval is user-configurable (2–30 s, default 5 s) via Settings → Devices → ECL 310 → Configure. Idle and slow intervals are hardcoded at 30 s.

## Project-specific notes

- **Domain**: `ecl310`; pip-audit packages: `pymodbus>=3.13.0`
- **Brand**: `custom_components/ecl310/brand/icon.png` + `brands/icon.png` (512×512 PNG — not yet committed, user must supply)
- **`.releaserc.json`** `prepareCmd` path: `custom_components/ecl310/manifest.json`
- **Sonometer 40**: exposed as a separate HA sub-device (`via_device=(DOMAIN, host)`); its sensors live in `sensor.py` as `SonometerSensorEntity`
- **Status registers** 4210/4211: raw integer sensors — value mapping unknown, update if Danfoss documentation clarifies
- **Saving temp bounds**: heating 5–26 °C, warmwater 40–75 °C (verify against device manual if needed)
