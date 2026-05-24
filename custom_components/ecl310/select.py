"""Select platform for Danfoss ECL 310 operating modes."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BaseEntity, ECL310Coordinator, KEY_COORDINATOR
from .const import (
    DOMAIN,
    OPERATING_MODES,
    REG_HEATING_OP_MODE,
    REG_WARMWATER_OP_MODE,
)
from .ecl310 import ECL310Device

PARALLEL_UPDATES = 1

_MODE_TO_INT: dict[str, int] = {v: k for k, v in OPERATING_MODES.items()}


@dataclass(frozen=True, kw_only=True)
class ECL310SelectDescription(SelectEntityDescription):
    """Select description with value accessor and register address."""

    address: int
    value_fn: Callable[[ECL310Device], int | None]


ECL310_SELECTS: tuple[ECL310SelectDescription, ...] = (
    ECL310SelectDescription(
        key="heating_op_mode",
        translation_key="heating_op_mode",
        options=list(OPERATING_MODES.values()),
        address=REG_HEATING_OP_MODE,
        value_fn=lambda d: d.heating_op_mode,
    ),
    ECL310SelectDescription(
        key="warmwater_op_mode",
        translation_key="warmwater_op_mode",
        options=list(OPERATING_MODES.values()),
        address=REG_WARMWATER_OP_MODE,
        value_fn=lambda d: d.warmwater_op_mode,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ECL 310 select entities."""
    coordinator: ECL310Coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]
    async_add_entities(
        ECL310SelectEntity(coordinator, description) for description in ECL310_SELECTS
    )


class ECL310SelectEntity(BaseEntity, SelectEntity):
    """An operating mode selector for the ECL 310."""

    entity_description: ECL310SelectDescription

    def __init__(
        self,
        coordinator: ECL310Coordinator,
        description: ECL310SelectDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self._host}_{description.key}"

    @property
    def current_option(self) -> str | None:
        raw = self.entity_description.value_fn(self._device)
        if raw is None:
            return None
        return OPERATING_MODES.get(raw)

    async def async_select_option(self, option: str) -> None:
        mode_int = _MODE_TO_INT[option]
        await self._device.async_set_operating_mode(
            self.entity_description.address, mode_int
        )
        await self.coordinator.async_request_refresh()
