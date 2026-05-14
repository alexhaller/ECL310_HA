"""Danfoss ECL 310 Modbus TCP device."""

from __future__ import annotations

import logging

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

_LOGGER = logging.getLogger(__name__)


def _s16(value: int) -> int:
    """Convert an unsigned 16-bit register value to signed."""
    return value if value < 32768 else value - 65536


def _u32(high: int, low: int) -> int:
    """Combine two 16-bit registers into an unsigned 32-bit value."""
    return (high << 16) | low


class ECL310Device:
    """Communicates with the ECL 310 via Modbus TCP."""

    def __init__(self, host: str, port: int, slave: int) -> None:
        self._host = host
        self._port = port
        self._slave = slave
        self._client: AsyncModbusTcpClient | None = None

        # Input register values
        self.outside_temp: float | None = None
        self.outside_temp_min: float | None = None
        self.outside_temp_max: float | None = None
        self.heating_flow_temp: float | None = None
        self.heating_return_temp: float | None = None
        self.warmwater_flow_temp: float | None = None
        self.warmwater_return_temp: float | None = None

        # Sonometer
        self.sonometer_t_flow: float | None = None
        self.sonometer_t_return: float | None = None
        self.sonometer_flow: float | None = None
        self.sonometer_power: float | None = None
        self.sonometer_volume: float | None = None
        self.sonometer_energy: float | None = None

        # Holding register values
        self.heating_op_mode: int | None = None
        self.warmwater_op_mode: int | None = None
        self.heating_status: int | None = None
        self.warmwater_status: int | None = None
        self.heating_comfort_temp: float | None = None
        self.heating_saving_temp: float | None = None
        self.warmwater_comfort_temp: float | None = None
        self.warmwater_saving_temp: float | None = None

    async def async_connect(self) -> None:
        """Open and verify the Modbus TCP connection."""
        if self._client is None:
            self._client = AsyncModbusTcpClient(host=self._host, port=self._port)
        if not self._client.connected:
            await self._client.connect()
            if not self._client.connected:
                raise ConnectionError(
                    f"Cannot connect to ECL310 at {self._host}:{self._port}"
                )

    async def async_close(self) -> None:
        """Close the Modbus TCP connection."""
        if self._client is not None:
            self._client.close()
            self._client = None

    async def async_update(self) -> None:
        """Read all registers from the device."""
        await self.async_connect()
        client = self._client
        assert client is not None
        slave = self._slave

        try:
            await self._read_sonometer(client, slave)
            await self._read_temperatures(client, slave)
            await self._read_outside_minmax(client, slave)
            await self._read_holding_modes(client, slave)
            await self._read_holding_status(client, slave)
            await self._read_holding_heating_setpoints(client, slave)
            await self._read_holding_warmwater_setpoints(client, slave)
        except ModbusException as err:
            raise ConnectionError(f"Modbus read error: {err}") from err

    async def _read_sonometer(self, client: AsyncModbusTcpClient, slave: int) -> None:
        result = await client.read_input_registers(6005, count=10, device_id=slave)
        if result.isError():
            _LOGGER.warning("Sonometer read failed")
            return
        r = result.registers
        self.sonometer_t_flow = round(_s16(r[0]) * 0.01, 2)
        self.sonometer_t_return = round(_s16(r[1]) * 0.01, 2)
        self.sonometer_flow = round(_u32(r[2], r[3]) * 0.1, 1)
        self.sonometer_power = round(_u32(r[4], r[5]) * 0.1, 1)
        self.sonometer_volume = round(_u32(r[6], r[7]) * 0.1, 1)
        self.sonometer_energy = round(_u32(r[8], r[9]) * 0.1, 0)

    async def _read_temperatures(
        self, client: AsyncModbusTcpClient, slave: int
    ) -> None:
        # 10200–10205: outside(0), unused(1), heat_flow(2), ww_flow(3), heat_ret(4), ww_ret(5)
        result = await client.read_input_registers(10200, count=6, device_id=slave)
        if result.isError():
            _LOGGER.warning("Temperature block read failed")
            return
        r = result.registers
        self.outside_temp = round(_s16(r[0]) * 0.01, 1)
        self.heating_flow_temp = round(_s16(r[2]) * 0.01, 1)
        self.warmwater_flow_temp = round(_s16(r[3]) * 0.01, 1)
        self.heating_return_temp = round(_s16(r[4]) * 0.01, 1)
        self.warmwater_return_temp = round(_s16(r[5]) * 0.01, 1)

    async def _read_outside_minmax(
        self, client: AsyncModbusTcpClient, slave: int
    ) -> None:
        # 10499 = min, 10504 = max — read 6 registers and pick indices 0 and 5
        result = await client.read_input_registers(10499, count=6, device_id=slave)
        if result.isError():
            _LOGGER.warning("Outside min/max read failed")
            return
        r = result.registers
        self.outside_temp_min = round(_s16(r[0]) * 0.01, 1)
        self.outside_temp_max = round(_s16(r[5]) * 0.01, 1)

    async def _read_holding_modes(
        self, client: AsyncModbusTcpClient, slave: int
    ) -> None:
        result = await client.read_holding_registers(4200, count=2, device_id=slave)
        if result.isError():
            _LOGGER.warning("Operating mode read failed")
            return
        r = result.registers
        self.heating_op_mode = r[0]
        self.warmwater_op_mode = r[1]

    async def _read_holding_status(
        self, client: AsyncModbusTcpClient, slave: int
    ) -> None:
        result = await client.read_holding_registers(4210, count=2, device_id=slave)
        if result.isError():
            _LOGGER.warning("Status read failed")
            return
        r = result.registers
        self.heating_status = r[0]
        self.warmwater_status = r[1]

    async def _read_holding_heating_setpoints(
        self, client: AsyncModbusTcpClient, slave: int
    ) -> None:
        result = await client.read_holding_registers(11179, count=2, device_id=slave)
        if result.isError():
            _LOGGER.warning("Heating setpoint read failed")
            return
        r = result.registers
        self.heating_comfort_temp = round(_s16(r[0]) * 0.1, 1)
        self.heating_saving_temp = round(_s16(r[1]) * 0.1, 1)

    async def _read_holding_warmwater_setpoints(
        self, client: AsyncModbusTcpClient, slave: int
    ) -> None:
        result = await client.read_holding_registers(12189, count=2, device_id=slave)
        if result.isError():
            _LOGGER.warning("Warmwater setpoint read failed")
            return
        r = result.registers
        self.warmwater_comfort_temp = round(_s16(r[0]) * 0.1, 1)
        self.warmwater_saving_temp = round(_s16(r[1]) * 0.1, 1)

    async def async_set_operating_mode(self, address: int, mode: int) -> None:
        """Write an operating mode to a holding register."""
        await self.async_connect()
        assert self._client is not None
        result = await self._client.write_register(address, mode, device_id=self._slave)
        if result.isError():
            raise ConnectionError(
                f"Failed to write operating mode to register {address}"
            )

    async def async_set_temperature(
        self, address: int, value: float, scale: float
    ) -> None:
        """Write a scaled temperature to a holding register."""
        await self.async_connect()
        assert self._client is not None
        raw = int(round(value / scale))
        result = await self._client.write_register(address, raw, device_id=self._slave)
        if result.isError():
            raise ConnectionError(f"Failed to write temperature to register {address}")
