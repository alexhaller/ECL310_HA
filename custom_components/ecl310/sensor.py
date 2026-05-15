"""Sensor platform for Danfoss ECL 310."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BaseEntity, ECL310Coordinator
from .const import DOMAIN, OPERATING_MODES
from .ecl310 import ECL310Device

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class ECL310SensorDescription(SensorEntityDescription):
    """Sensor description with value accessor."""

    value_fn: Callable[[ECL310Device], float | int | str | None]


ECL310_SENSORS: tuple[ECL310SensorDescription, ...] = (
    ECL310SensorDescription(
        key="outside_temp",
        translation_key="outside_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.outside_temp,
    ),
    ECL310SensorDescription(
        key="outside_temp_min",
        translation_key="outside_temp_min",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.outside_temp_min,
    ),
    ECL310SensorDescription(
        key="outside_temp_max",
        translation_key="outside_temp_max",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.outside_temp_max,
    ),
    ECL310SensorDescription(
        key="heating_flow_temp",
        translation_key="heating_flow_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.heating_flow_temp,
    ),
    ECL310SensorDescription(
        key="heating_return_temp",
        translation_key="heating_return_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.heating_return_temp,
    ),
    ECL310SensorDescription(
        key="heating_status",
        translation_key="heating_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.heating_status,
    ),
    ECL310SensorDescription(
        key="warmwater_flow_temp",
        translation_key="warmwater_flow_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.warmwater_flow_temp,
    ),
    ECL310SensorDescription(
        key="warmwater_return_temp",
        translation_key="warmwater_return_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.warmwater_return_temp,
    ),
    ECL310SensorDescription(
        key="warmwater_status",
        translation_key="warmwater_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.warmwater_status,
    ),
    ECL310SensorDescription(
        key="heating_active_mode",
        translation_key="heating_active_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: (
            OPERATING_MODES.get(d.heating_op_mode)
            if d.heating_op_mode is not None
            else None
        ),
    ),
    ECL310SensorDescription(
        key="warmwater_active_mode",
        translation_key="warmwater_active_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: (
            OPERATING_MODES.get(d.warmwater_op_mode)
            if d.warmwater_op_mode is not None
            else None
        ),
    ),
)

SONOMETER_SENSORS: tuple[ECL310SensorDescription, ...] = (
    ECL310SensorDescription(
        key="sonometer_t_flow",
        translation_key="sonometer_t_flow",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.sonometer_t_flow,
    ),
    ECL310SensorDescription(
        key="sonometer_t_return",
        translation_key="sonometer_t_return",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.sonometer_t_return,
    ),
    ECL310SensorDescription(
        key="sonometer_flow",
        translation_key="sonometer_flow",
        native_unit_of_measurement="L/h",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.sonometer_flow,
    ),
    ECL310SensorDescription(
        key="sonometer_power",
        translation_key="sonometer_power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.sonometer_power,
    ),
    ECL310SensorDescription(
        key="sonometer_volume",
        translation_key="sonometer_volume",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.VOLUME,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda d: d.sonometer_volume,
    ),
    ECL310SensorDescription(
        key="sonometer_energy",
        translation_key="sonometer_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda d: d.sonometer_energy,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ECL 310 sensors."""
    coordinator: ECL310Coordinator = hass.data[DOMAIN][entry.entry_id]
    host: str = entry.data[CONF_HOST]

    entities: list[ECL310SensorEntity | SonometerSensorEntity] = [
        ECL310SensorEntity(coordinator, description) for description in ECL310_SENSORS
    ]
    entities += [
        SonometerSensorEntity(coordinator, description, host)
        for description in SONOMETER_SENSORS
    ]
    async_add_entities(entities)


class ECL310SensorEntity(BaseEntity, SensorEntity):
    """A sensor entity for the ECL 310 main device."""

    entity_description: ECL310SensorDescription

    def __init__(
        self,
        coordinator: ECL310Coordinator,
        description: ECL310SensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self._host}_{description.key}"

    @property
    def native_value(self) -> float | int | str | None:
        return self.entity_description.value_fn(self._device)


class SonometerSensorEntity(BaseEntity, SensorEntity):
    """A sensor entity for the Sonometer 40 sub-device."""

    entity_description: ECL310SensorDescription

    def __init__(
        self,
        coordinator: ECL310Coordinator,
        description: ECL310SensorDescription,
        host: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{host}_sonometer_{description.key}"
        self._sonometer_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{host}_sonometer")},
            name="Sonometer 40",
            manufacturer="Danfoss",
            model="Sonometer 40",
            via_device=(DOMAIN, host),
        )

    @property
    def device_info(self) -> DeviceInfo:
        return self._sonometer_device_info

    @property
    def native_value(self) -> float | int | str | None:
        return self.entity_description.value_fn(self._device)
