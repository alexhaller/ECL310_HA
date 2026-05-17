"""Danfoss ECL 310 integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_ACTIVE_INTERVAL,
    CONF_SLAVE,
    DEFAULT_ACTIVE_INTERVAL,
    IDLE_INTERVAL_S,
    SLOW_INTERVAL_S,
    DOMAIN,
)
from .ecl310 import ECL310Device

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER, Platform.SELECT]

KEY_COORDINATOR = "coordinator"
KEY_SLOW_COORDINATOR = "slow_coordinator"

type ECL310Coordinator = DataUpdateCoordinator[ECL310Device]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ECL 310 from a config entry."""
    host: str = entry.data[CONF_HOST]
    port: int = entry.data[CONF_PORT]
    slave: int = entry.data[CONF_SLAVE]

    device = ECL310Device(host=host, port=port, slave=slave)
    active_s = int(entry.options.get(CONF_ACTIVE_INTERVAL, DEFAULT_ACTIVE_INTERVAL))

    async def _async_update_slow() -> ECL310Device:
        try:
            await device.async_update_slow()
        except Exception as err:
            raise UpdateFailed(f"ECL310 slow update failed: {err}") from err
        return device

    async def _async_update_fast() -> ECL310Device:
        try:
            await device.async_update_fast()
        except Exception as err:
            raise UpdateFailed(f"ECL310 fast update failed: {err}") from err
        flowing = (device.sonometer_flow or 0) > 0
        new_interval = timedelta(seconds=active_s if flowing else IDLE_INTERVAL_S)
        if adaptive_coordinator.update_interval != new_interval:
            adaptive_coordinator.update_interval = new_interval
        return device

    slow_coordinator: ECL310Coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_slow",
        update_method=_async_update_slow,
        update_interval=timedelta(seconds=SLOW_INTERVAL_S),
    )

    adaptive_coordinator: ECL310Coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_adaptive",
        update_method=_async_update_fast,
        update_interval=timedelta(seconds=IDLE_INTERVAL_S),
    )

    await slow_coordinator.async_config_entry_first_refresh()
    await adaptive_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        KEY_COORDINATOR: adaptive_coordinator,
        KEY_SLOW_COORDINATOR: slow_coordinator,
    }

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        device: ECL310Device = data[KEY_COORDINATOR].data
        await device.async_close()
    return unload_ok


class BaseEntity(CoordinatorEntity[ECL310Coordinator]):
    """Base entity for ECL 310 integration."""

    has_entity_name = True

    def __init__(self, coordinator: ECL310Coordinator) -> None:
        super().__init__(coordinator)
        self._device = coordinator.data

    @property
    def _host(self) -> str:
        entry = self.coordinator.config_entry
        assert entry is not None
        return str(entry.data[CONF_HOST])

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._host)},
            name="Danfoss ECL 310",
            manufacturer="Danfoss",
            model="ECL 310",
        )

    def _handle_coordinator_update(self) -> None:
        self._device = self.coordinator.data
        super()._handle_coordinator_update()
