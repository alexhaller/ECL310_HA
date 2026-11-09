"""Danfoss ECL 310 integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
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
    DOMAIN,
    IDLE_INTERVAL_S,
    SLOW_INTERVAL_S,
)
from .ecl310 import ECL310Device

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER, Platform.SELECT]

type ECL310Coordinator = DataUpdateCoordinator[ECL310Device]


@dataclass
class ECL310Data:
    """What a loaded config entry holds."""

    coordinator: ECL310Coordinator
    slow_coordinator: ECL310Coordinator
    device: ECL310Device
    main_device_id: str


type ECL310ConfigEntry = ConfigEntry[ECL310Data]


def stable_id(entry: ConfigEntry) -> str:
    """Return the id devices and entities are keyed on.

    It is the host the entry was created with. It stays the same when the
    host is changed with Reconfigure, so the entities keep their history.
    """
    return entry.unique_id or str(entry.data[CONF_HOST])


def main_device_info(base_id: str) -> DeviceInfo:
    """Device info of the ECL 310 controller itself."""
    return DeviceInfo(
        identifiers={(DOMAIN, base_id)},
        name="Danfoss ECL 310",
        manufacturer="Danfoss",
        model="ECL 310",
    )


async def async_setup_entry(hass: HomeAssistant, entry: ECL310ConfigEntry) -> bool:
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
        config_entry=entry,
        name=f"{DOMAIN}_slow",
        update_method=_async_update_slow,
        update_interval=timedelta(seconds=SLOW_INTERVAL_S),
    )

    adaptive_coordinator: ECL310Coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        config_entry=entry,
        name=f"{DOMAIN}_adaptive",
        update_method=_async_update_fast,
        update_interval=timedelta(seconds=IDLE_INTERVAL_S),
    )

    try:
        await slow_coordinator.async_config_entry_first_refresh()
        await adaptive_coordinator.async_config_entry_first_refresh()
    except BaseException:
        # Setup is retried with a new device; without this the Modbus client of
        # every failed attempt would stay behind and keep reconnecting.
        await device.async_close()
        raise

    # The Sonometer 40 links to the controller via `via_device_id`, which needs the
    # registry id of an already registered device, so register the controller here
    # instead of leaving it to the first entity being added.
    main_device = dr.async_get(hass).async_get_or_create_from_info(
        config_entry_id=entry.entry_id,
        device_info=main_device_info(stable_id(entry)),
    )

    entry.runtime_data = ECL310Data(
        coordinator=adaptive_coordinator,
        slow_coordinator=slow_coordinator,
        device=device,
        main_device_id=main_device.id,
    )

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ECL310ConfigEntry) -> None:
    """Reload the config entry when its options or connection details change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ECL310ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.device.async_close()
    return unload_ok


class BaseEntity(CoordinatorEntity[ECL310Coordinator]):
    """Base entity for ECL 310 integration."""

    has_entity_name = True

    def __init__(self, coordinator: ECL310Coordinator) -> None:
        super().__init__(coordinator)
        self._device = coordinator.data

    @property
    def _base_id(self) -> str:
        entry = self.coordinator.config_entry
        assert entry is not None
        return stable_id(entry)

    @property
    def device_info(self) -> DeviceInfo:
        return main_device_info(self._base_id)

    def _handle_coordinator_update(self) -> None:
        self._device = self.coordinator.data
        super()._handle_coordinator_update()
