"""Number platform for Danfoss ECL 310 temperature setpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BaseEntity, ECL310Coordinator, KEY_COORDINATOR
from .const import (
    DOMAIN,
    REG_HEATING_COMFORT_TEMP,
    REG_HEATING_SAVING_TEMP,
    REG_WARMWATER_COMFORT_TEMP,
    REG_WARMWATER_SAVING_TEMP,
)
from .ecl310 import ECL310Device

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class ECL310NumberDescription(NumberEntityDescription):
    """Number description with value accessor and register address."""

    address: int
    scale: float
    value_fn: Callable[[ECL310Device], float | None]


ECL310_NUMBERS: tuple[ECL310NumberDescription, ...] = (
    ECL310NumberDescription(
        key="heating_comfort_temp",
        translation_key="heating_comfort_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.BOX,
        native_min_value=0.0,
        native_max_value=26.0,
        native_step=0.1,
        address=REG_HEATING_COMFORT_TEMP,
        scale=0.1,
        value_fn=lambda d: d.heating_comfort_temp,
    ),
    ECL310NumberDescription(
        key="heating_saving_temp",
        translation_key="heating_saving_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.BOX,
        native_min_value=5.0,
        native_max_value=26.0,
        native_step=0.1,
        address=REG_HEATING_SAVING_TEMP,
        scale=0.1,
        value_fn=lambda d: d.heating_saving_temp,
    ),
    ECL310NumberDescription(
        key="warmwater_comfort_temp",
        translation_key="warmwater_comfort_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.BOX,
        native_min_value=40.0,
        native_max_value=80.0,
        native_step=0.1,
        address=REG_WARMWATER_COMFORT_TEMP,
        scale=0.1,
        value_fn=lambda d: d.warmwater_comfort_temp,
    ),
    ECL310NumberDescription(
        key="warmwater_saving_temp",
        translation_key="warmwater_saving_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.BOX,
        native_min_value=40.0,
        native_max_value=80.0,
        native_step=0.1,
        address=REG_WARMWATER_SAVING_TEMP,
        scale=0.1,
        value_fn=lambda d: d.warmwater_saving_temp,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ECL 310 number entities."""
    coordinator: ECL310Coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]
    async_add_entities(
        ECL310NumberEntity(coordinator, description) for description in ECL310_NUMBERS
    )


class ECL310NumberEntity(BaseEntity, NumberEntity):
    """A writable temperature setpoint for the ECL 310."""

    entity_description: ECL310NumberDescription

    def __init__(
        self,
        coordinator: ECL310Coordinator,
        description: ECL310NumberDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self._host}_{description.key}"

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self._device)

    async def async_set_native_value(self, value: float) -> None:
        await self._device.async_set_temperature(
            self.entity_description.address,
            value,
            self.entity_description.scale,
        )
        await self.coordinator.async_request_refresh()
