"""Setup, entities, devices and the adaptive poll interval of the ECL 310."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from homeassistant.components.number import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.components.select import ATTR_OPTION, SERVICE_SELECT_OPTION
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant.common import MockConfigEntry

from custom_components.ecl310.const import (
    DOMAIN,
    IDLE_INTERVAL_S,
    REG_HEATING_COMFORT_TEMP,
    REG_HEATING_OP_MODE,
)

from .conftest import HOST, FakeModbusClient


def _entity_id(hass: HomeAssistant, platform: str, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{HOST}_{key}"
    )
    assert entity_id is not None, key
    return entity_id


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_creates_entities(
    hass: HomeAssistant,
    modbus: type[FakeModbusClient],
    config_entry: MockConfigEntry,
) -> None:
    await _setup(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED
    outside = hass.states.get(_entity_id(hass, "sensor", "outside_temp"))
    assert outside is not None
    assert float(outside.state) == -3.5
    comfort = hass.states.get(_entity_id(hass, "number", "heating_comfort_temp"))
    assert comfort is not None
    assert float(comfort.state) == 21.5
    mode = hass.states.get(_entity_id(hass, "select", "heating_op_mode"))
    assert mode is not None
    assert mode.state == "scheduled"


async def test_sonometer_is_a_device_behind_the_controller(
    hass: HomeAssistant,
    modbus: type[FakeModbusClient],
    config_entry: MockConfigEntry,
) -> None:
    await _setup(hass, config_entry)

    registry = dr.async_get(hass)
    controller = registry.async_get_device_by_identifier(
        (DOMAIN, HOST), config_entry.entry_id
    )
    sonometer = registry.async_get_device_by_identifier(
        (DOMAIN, f"{HOST}_sonometer"), config_entry.entry_id
    )
    assert controller is not None
    assert sonometer is not None
    assert sonometer.via_device_id == controller.id


async def test_number_writes_scaled_value(
    hass: HomeAssistant,
    modbus: type[FakeModbusClient],
    config_entry: MockConfigEntry,
) -> None:
    await _setup(hass, config_entry)
    entity_id = _entity_id(hass, "number", "heating_comfort_temp")

    await hass.services.async_call(
        "number",
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 22.0},
        blocking=True,
    )

    assert (REG_HEATING_COMFORT_TEMP, 220) in modbus.instances[0].writes
    assert float(hass.states.get(entity_id).state) == 22.0


async def test_select_writes_mode(
    hass: HomeAssistant,
    modbus: type[FakeModbusClient],
    config_entry: MockConfigEntry,
) -> None:
    await _setup(hass, config_entry)

    await hass.services.async_call(
        "select",
        SERVICE_SELECT_OPTION,
        {
            ATTR_ENTITY_ID: _entity_id(hass, "select", "heating_op_mode"),
            ATTR_OPTION: "comfort",
        },
        blocking=True,
    )

    assert (REG_HEATING_OP_MODE, 2) in modbus.instances[0].writes


async def test_poll_speeds_up_while_heat_flows(
    hass: HomeAssistant,
    modbus: type[FakeModbusClient],
    config_entry: MockConfigEntry,
) -> None:
    await _setup(hass, config_entry)
    coordinator = config_entry.runtime_data.coordinator
    assert coordinator.update_interval == timedelta(seconds=IDLE_INTERVAL_S)

    modbus.instances[0].input[6008] = 125  # flow 12.5
    await coordinator.async_refresh()
    assert coordinator.update_interval == timedelta(seconds=5)

    modbus.instances[0].input[6008] = 0
    await coordinator.async_refresh()
    assert coordinator.update_interval == timedelta(seconds=IDLE_INTERVAL_S)


async def test_unload_closes_the_connection(
    hass: HomeAssistant,
    modbus: type[FakeModbusClient],
    config_entry: MockConfigEntry,
) -> None:
    await _setup(hass, config_entry)
    assert modbus.instances[0].connected

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert not modbus.instances[0].connected


async def test_failed_setup_closes_the_connection(
    hass: HomeAssistant,
    modbus: type[FakeModbusClient],
    config_entry: MockConfigEntry,
) -> None:
    """Every retry builds a new client; a failed one must not stay behind."""
    with patch.object(FakeModbusClient, "close", autospec=True) as close:
        with patch.object(
            FakeModbusClient, "connect", autospec=True, return_value=False
        ):
            config_entry.add_to_hass(hass)
            await hass.config_entries.async_setup(config_entry.entry_id)
            await hass.async_block_till_done()

        assert config_entry.state is ConfigEntryState.SETUP_RETRY
        assert close.call_count == len(modbus.instances) >= 1


async def test_diagnostics(
    hass: HomeAssistant,
    modbus: type[FakeModbusClient],
    config_entry: MockConfigEntry,
) -> None:
    from custom_components.ecl310.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    await _setup(hass, config_entry)

    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diagnostics["entry"]["data"]["host"] == HOST
    assert diagnostics["values"]["outside_temp"] == -3.5
    assert diagnostics["failed_register_blocks"] == []
    assert set(diagnostics["coordinators"]) == {"ecl310_adaptive", "ecl310_slow"}
