# Danfoss ECL 310 for Home Assistant

A Home Assistant integration for the **Danfoss ECL Comfort 310** district heating
controller. It reads temperatures, operating states and setpoints over Modbus TCP,
and lets you change the comfort/saving setpoints and the operating modes of the
heating and warm water circuits. If a **Danfoss Sonometer 40** heat meter is
connected to the controller, its readings appear as a second device.

## Requirements

- Home Assistant 2026.11 or newer.
- An ECL Comfort 310 connected to your network through its Ethernet port, with
  Modbus TCP reachable from Home Assistant (port 502 by default). The integration
  talks to the controller directly on your network; no cloud account is needed.
- Optional: a Sonometer 40 connected to the ECL 310 over M-Bus. To make its values
  available, scan for it once on the controller: **Configuration > M-Bus > Scan**.

## Installation

1. In Home Assistant, open the Marketplace (HACS), search for
   **Danfoss ECL 310** and download it.
2. Restart Home Assistant.

## Setup

Go to **Settings > Devices & services > Add integration** and choose
**Danfoss ECL 310**.

| Field | Description |
|---|---|
| Host | IP address or hostname of the ECL 310 |
| Modbus TCP port | TCP port of the controller's Modbus server; default **502** |
| Slave ID | Modbus unit identifier of the controller; default **1** |

The integration connects once to check the details before it creates the entry.

If the controller later gets a different address, open the integration and
choose **Reconfigure** (three-dot menu). The entities and their history are kept.

### Options

Open the integration and choose **Configure** to set the **active polling
interval** (2–30 seconds, default 5). See *Polling* below.

## Entities

### ECL 310

| Entity | Type | Description |
|---|---|---|
| Outside Temperature | Sensor (°C) | Current outside temperature |
| Outside Temperature Min / Max | Sensor (°C) | Lowest / highest outside temperature recorded by the controller |
| Heating Flow / Return Temperature | Sensor (°C) | Heating circuit flow and return |
| Warm Water Flow / Return Temperature | Sensor (°C) | Warm water circuit flow and return |
| Heating / Warm Water Status | Sensor | Raw circuit status code as reported by the controller |
| Heating / Warm Water Operating Mode Status | Sensor | Raw operating mode status code |
| Heating Operating Mode | Select | Manual, Scheduled, Comfort, Setback or Frost Protection |
| Warm Water Operating Mode | Select | Manual, Scheduled, Comfort, Setback or Frost Protection |
| Heating Comfort Temperature | Number (°C) | Room temperature in comfort mode, 0–26 °C |
| Heating Saving Temperature | Number (°C) | Room temperature in saving mode, 5–26 °C |
| Warm Water Comfort / Saving Temperature | Number (°C) | Warm water temperature in comfort / saving mode, 40–80 °C |

### Sonometer 40

Shown as a separate device connected through the ECL 310.

| Entity | Type | Description |
|---|---|---|
| Primary Flow / Return Temperature | Sensor (°C) | District heating supply and return at the meter |
| Flow Rate | Sensor (L/h) | Current flow |
| Power | Sensor (kW) | Current heat power |
| Volume | Sensor (m³) | Total volume |
| Energy | Sensor (kWh) | Total heat energy, usable in the Energy dashboard |

> **The number and select entities write to the controller.** Changing a
> setpoint or an operating mode in Home Assistant changes it on the ECL 310
> itself, exactly as if you had changed it on the device. If the controller
> rejects a value, Home Assistant shows the Modbus exception code it returned.

## Polling

- Outside temperatures, circuit status codes and the Sonometer totals are read
  every 30 seconds.
- Everything else is polled **adaptively**: every 30 seconds while no heat flows,
  and at the active polling interval (default 5 seconds) while the Sonometer
  reports a flow, so you see temperatures and power change while heat is being
  drawn.

Both use one Modbus TCP connection to the controller.

## Troubleshooting

- **Unable to connect**: check that the controller's IP address is reachable from
  Home Assistant and that nothing else blocks TCP port 502. Some setups use a
  slave ID other than 1.
- **No Sonometer values**: run the M-Bus scan on the controller (see
  *Requirements*).
- **Values show as unknown**: the controller refused that register block. The
  log names the block once when it starts and once when it works again.
- **Download diagnostics** on the integration page collects the settings and the
  last values read, which helps when reporting a problem.
- To see the raw Modbus traffic, enable debug logging for the integration under
  **Settings > Devices & services > Danfoss ECL 310 > Enable debug logging**.

## License

MIT, see [LICENSE](LICENSE).
