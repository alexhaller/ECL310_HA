# CLAUDE.md — ECL310_HA

## Project overview

Custom Home Assistant integration for the Danfoss ECL 310 district heating controller. Communicates via Modbus TCP (default port 502, slave ID 1). The Modbus register map is fixed per the ECL 310 datasheet — do not change register addresses without verifying against the device documentation.

- GitHub: https://github.com/alexhaller/ECL310_HA

Key files:
- `custom_components/ecl310/ecl310.py` — device communication layer; all Modbus reads/writes; `async_update()` reads 7 register blocks per poll cycle
- `custom_components/ecl310/__init__.py` — coordinator (30 s poll interval), `BaseEntity`, `async_setup_entry`, `async_unload_entry`
- `custom_components/ecl310/config_flow.py` — required user inputs: host, port (default 502), slave_id (default 1)
- `custom_components/ecl310/const.py` — DOMAIN, all register address constants, OPERATING_MODES mapping
- Platforms: `sensor.py` (21 sensors), `number.py` (4 setpoints), `select.py` (2 operating modes)

## Project-specific notes

- **Domain**: `ecl310`; pip-audit packages: `pymodbus>=3.13.0`
- **Brand**: `custom_components/ecl310/brand/icon.png` + `brands/icon.png` (512×512 PNG — not yet committed, user must supply)
- **`.releaserc.json`** `prepareCmd` path: `custom_components/ecl310/manifest.json`
- **Sonometer 40**: exposed as a separate HA sub-device (`via_device=(DOMAIN, host)`); its sensors live in `sensor.py` as `SonometerSensorEntity`
- **Status registers** 4210/4211: raw integer sensors — value mapping unknown, update if Danfoss documentation clarifies
- **Saving temp bounds**: heating 5–26 °C, warmwater 40–75 °C (verify against device manual if needed)
