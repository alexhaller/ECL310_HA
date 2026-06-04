# CLAUDE.md — ECL310_HA

## Project overview

Custom Home Assistant integration for the Danfoss ECL 310 district heating controller. Communicates via Modbus TCP (default port 502, slave ID 1). The Modbus register map is fixed per the ECL 310 datasheet — do not change register addresses without verifying against the device documentation.

- GitHub: https://github.com/alexhaller/ECL310_HA
- Project forked from: -

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

## Danfoss documentation references

- **ECL 310 Modbus communication description**: https://assets.danfoss.com/documents/206108/AQ074886472234en-010602.pdf
- **Sonometer 40 datasheet / M-Bus setup guide**: https://assets.danfoss.com/documents/191069/AQ390129194620en-010101.pdf

### Modbus address mapping

The Danfoss documentation uses **PNU** (Parameter Number) to identify registers. The Modbus register address used in code is always **PNU − 1**:

```
Modbus address = Danfoss PNU − 1
```

Example: Danfoss PNU 10201 → Modbus register 10200 (`REG_OUTSIDE_TEMP`).

### 32-bit registers ("low part")

When the Danfoss docs describe a value as having a "low part", the value spans two consecutive 16-bit Modbus registers and must be combined into a 32-bit integer. This applies to sonometer flow, power, volume, and energy — handled by `_u32(high, low)` in `ecl310.py`.

### Sonometer 40 M-Bus integration

The Sonometer 40 is connected to the ECL 310 via M-Bus (not directly via Modbus/TCP). To activate it: ECL menu → Configuration → M-Bus → Scan. After scanning, the Sonometer registers (6005–6014) become readable via Modbus TCP on the ECL 310.

## Project-specific notes

- **Domain**: `ecl310`; `requirements: []` — pymodbus is bundled by HA core, not listed
- **Brand**: `custom_components/ecl310/brand/icon.png` + `brands/icon.png` (512×512 PNG — not yet committed, user must supply)
- **`.releaserc.json`** `prepareCmd` path: `custom_components/ecl310/manifest.json`
- **Sonometer 40**: exposed as a separate HA sub-device (`via_device=(DOMAIN, host)`); its sensors live in `sensor.py` as `SonometerSensorEntity`
- **Status registers** 4210/4211: raw integer sensors — value mapping unknown, update if Danfoss documentation clarifies
- **Saving temp bounds**: heating 5–26 °C, warmwater 40–75 °C (verify against device manual if needed)
