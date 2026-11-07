"""Fixtures for the Danfoss ECL 310 tests: a Modbus client serving a register map."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass, field
from typing import ClassVar
from unittest.mock import patch

import pytest
from pymodbus.pdu import ExceptionResponse
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecl310.const import CONF_SLAVE, DOMAIN

pytest_plugins = "pytest_homeassistant_custom_component"

HOST = "192.168.1.50"
ENTRY_DATA = {"host": HOST, "port": 502, CONF_SLAVE: 1}


def _temp(celsius: float, scale: float = 0.01) -> int:
    """Encode a temperature the way the controller does: signed 16 bit, scaled."""
    return round(celsius / scale) & 0xFFFF


def _u32(value: int) -> list[int]:
    return [value >> 16, value & 0xFFFF]


# Register map of a unit at rest: no sonometer flow
INPUT_REGISTERS: dict[int, int] = {
    10200: _temp(-3.5),  # outside
    10202: _temp(45.0),  # heating flow
    10203: _temp(52.0),  # warm water flow
    10204: _temp(35.0),  # heating return
    10205: _temp(30.0),  # warm water return
    10499: _temp(-8.0),  # outside min
    10504: _temp(12.0),  # outside max
    6005: _temp(60.0),  # sonometer flow temp
    6006: _temp(40.0),  # sonometer return temp
    **dict(zip(range(6007, 6009), _u32(0), strict=True)),  # flow
    **dict(zip(range(6009, 6011), _u32(0), strict=True)),  # power
    **dict(zip(range(6011, 6013), _u32(12345), strict=True)),  # volume
    **dict(zip(range(6013, 6015), _u32(67890), strict=True)),  # energy
}
HOLDING_REGISTERS: dict[int, int] = {
    4200: 1,  # heating mode: scheduled
    4201: 2,  # warm water mode: comfort
    4210: 3,
    4211: 4,
    11179: 215,  # heating comfort 21.5
    11180: 170,  # heating saving 17.0
    12189: 550,  # warm water comfort 55.0
    12190: 450,  # warm water saving 45.0
}


@dataclass
class _Result:
    registers: list[int] = field(default_factory=list)

    def isError(self) -> bool:
        return False


class FakeModbusClient:
    """Stands in for AsyncModbusTcpClient; reads and writes a register map."""

    instances: ClassVar[list[FakeModbusClient]] = []

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.connected = False
        self.input = dict(INPUT_REGISTERS)
        self.holding = dict(HOLDING_REGISTERS)
        self.writes: list[tuple[int, int]] = []
        self.reject_writes_with: int | None = None
        FakeModbusClient.instances.append(self)

    async def connect(self) -> bool:
        self.connected = True
        return True

    def close(self) -> None:
        self.connected = False

    async def read_input_registers(self, address: int, count: int, device_id: int):
        return _Result([self.input[a] for a in range(address, address + count)])

    async def read_holding_registers(self, address: int, count: int, device_id: int):
        return _Result([self.holding[a] for a in range(address, address + count)])

    async def write_register(self, address: int, value: int, device_id: int):
        if self.reject_writes_with is not None:
            return ExceptionResponse(6, exception_code=self.reject_writes_with)
        self.writes.append((address, value))
        self.holding[address] = value
        return _Result()


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable the integration under custom_components."""


@pytest.fixture
def modbus() -> Generator[type[FakeModbusClient]]:
    """Replace the Modbus client; the created clients are in .instances."""
    FakeModbusClient.instances = []
    with patch(
        "custom_components.ecl310.ecl310.AsyncModbusTcpClient", FakeModbusClient
    ):
        yield FakeModbusClient


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN, title=f"ECL 310 ({HOST})", unique_id=HOST, data=ENTRY_DATA
    )
