"""Diagnostics for the Danfoss ECL 310 integration."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import ECL310ConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ECL310ConfigEntry
) -> dict[str, Any]:
    """Return the connection settings and the last values read."""
    data = entry.runtime_data
    return {
        "entry": {"data": dict(entry.data), "options": dict(entry.options)},
        "coordinators": {
            coordinator.name: {
                "last_update_success": coordinator.last_update_success,
                "update_interval_s": coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None,
            }
            for coordinator in (data.coordinator, data.slow_coordinator)
        },
        # Only readings and setpoints; the controller holds nothing secret
        "values": {
            key: value
            for key, value in vars(data.device).items()
            if not key.startswith("_")
        },
        "failed_register_blocks": sorted(data.device.failed_blocks),
    }
