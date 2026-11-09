"""Register decoding and writes of the ECL 310 device layer."""

from __future__ import annotations

import logging

import pytest
from homeassistant.exceptions import HomeAssistantError
from pymodbus.exceptions import ModbusIOException

from custom_components.ecl310.const import REG_HEATING_COMFORT_TEMP
from custom_components.ecl310.ecl310 import ECL310Device, _temp

from .conftest import HOST, FakeModbusClient


@pytest.fixture
async def device(modbus: type[FakeModbusClient]) -> ECL310Device:
    unit = ECL310Device(host=HOST, port=502, slave=1)
    await unit.async_update_slow()
    await unit.async_update_fast()
    return unit


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(2150, 21.5), ((-350) & 0xFFFF, -3.5), (0x7FFF, None), (0x8000, None)],
)
def test_temperature_decoding(raw: int, expected: float | None) -> None:
    """Signed, scaled by 0.01; the controller's sentinels fall outside -40..130."""
    assert _temp(raw) == expected


async def test_slow_registers(device: ECL310Device) -> None:
    assert device.outside_temp == -3.5
    assert device.outside_temp_min == -8.0
    assert device.outside_temp_max == 12.0
    assert device.heating_status == 3
    assert device.warmwater_status == 4
    assert device.sonometer_volume == 1234.5
    assert device.sonometer_energy == 6789.0


async def test_fast_registers(device: ECL310Device) -> None:
    assert device.heating_flow_temp == 45.0
    assert device.warmwater_flow_temp == 52.0
    assert device.heating_return_temp == 35.0
    assert device.warmwater_return_temp == 30.0
    assert device.sonometer_t_flow == 60.0
    assert device.sonometer_t_return == 40.0
    assert device.sonometer_flow == 0.0
    assert device.heating_op_mode == 1
    assert device.warmwater_op_mode == 2
    assert device.heating_comfort_temp == 21.5
    assert device.heating_saving_temp == 17.0
    assert device.warmwater_comfort_temp == 55.0
    assert device.warmwater_saving_temp == 45.0


async def test_write_temperature_is_scaled(device: ECL310Device) -> None:
    await device.async_set_temperature(REG_HEATING_COMFORT_TEMP, 22.3, 0.1)
    assert FakeModbusClient.instances[0].writes == [(REG_HEATING_COMFORT_TEMP, 223)]


async def test_rejected_write_names_the_exception(device: ECL310Device) -> None:
    """The device's exception code tells a busy unit from an out-of-range value."""
    FakeModbusClient.instances[0].reject_writes_with = 6

    with pytest.raises(HomeAssistantError, match="exception_code=6"):
        await device.async_set_temperature(REG_HEATING_COMFORT_TEMP, 21.5, 0.1)


async def test_unreachable_controller_on_write_is_a_clear_error(
    device: ECL310Device,
) -> None:
    FakeModbusClient.instances[0].fail_writes_with = ModbusIOException("no reply")

    with pytest.raises(HomeAssistantError, match="Cannot reach the ECL 310"):
        await device.async_set_temperature(REG_HEATING_COMFORT_TEMP, 21.5, 0.1)


async def test_refused_block_clears_its_values_and_warns_once(
    device: ECL310Device, caplog: pytest.LogCaptureFixture
) -> None:
    """Stale values must not look current, and the log must not fill up."""
    client = FakeModbusClient.instances[0]
    client.refuse_reads = {10202}

    with caplog.at_level(logging.INFO):
        await device.async_update_fast()
        await device.async_update_fast()

    assert device.heating_flow_temp is None
    assert device.warmwater_return_temp is None
    # Other blocks of the same poll are unaffected
    assert device.heating_comfort_temp == 21.5
    assert device.failed_blocks == {"Circuit temperature"}
    assert caplog.text.count("Circuit temperature read failed") == 1

    client.refuse_reads = set()
    with caplog.at_level(logging.INFO):
        await device.async_update_fast()

    assert device.heating_flow_temp == 45.0
    assert device.failed_blocks == frozenset()
    assert "Circuit temperature read works again" in caplog.text
