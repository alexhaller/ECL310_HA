"""Config and options flow of the ECL 310 integration."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from pytest_homeassistant.common import MockConfigEntry

from custom_components.ecl310.const import CONF_ACTIVE_INTERVAL, CONF_SLAVE, DOMAIN

from .conftest import ENTRY_DATA, HOST


async def _submit(hass: HomeAssistant, user_input: dict) -> dict:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


@pytest.mark.usefixtures("modbus")
async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    result = await _submit(hass, {"host": f"  {HOST} "})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"ECL 310 ({HOST})"
    assert result["data"] == ENTRY_DATA
    assert result["result"].unique_id == HOST


@pytest.mark.usefixtures("modbus")
async def test_invalid_host(hass: HomeAssistant) -> None:
    result = await _submit(hass, {"host": "not a host"})

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"host": "invalid_host"}


async def test_cannot_connect(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.ecl310.config_flow.ECL310Device.async_connect",
        side_effect=ConnectionError,
    ):
        result = await _submit(hass, {"host": HOST})

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


@pytest.mark.usefixtures("modbus")
async def test_already_configured(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)

    result = await _submit(hass, {"host": HOST, "port": 502, CONF_SLAVE: 1})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_bounds_the_active_interval(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    with pytest.raises(InvalidData, match=CONF_ACTIVE_INTERVAL):
        await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_ACTIVE_INTERVAL: 60}
        )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_ACTIVE_INTERVAL: 10}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {CONF_ACTIVE_INTERVAL: 10}


@pytest.mark.usefixtures("modbus")
async def test_reconfigure_moves_the_host_and_keeps_the_identity(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Entities are keyed on the unique id, so it must survive a new host."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "192.168.1.99", "port": 1502, CONF_SLAVE: 2}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data == {"host": "192.168.1.99", "port": 1502, CONF_SLAVE: 2}
    assert config_entry.unique_id == HOST
    assert config_entry.title == "ECL 310 (192.168.1.99)"


@pytest.mark.usefixtures("modbus")
async def test_reconfigure_refuses_the_host_of_another_entry(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.99",
        data={**ENTRY_DATA, "host": "192.168.1.99"},
    ).add_to_hass(hass)
    result = await config_entry.start_reconfigure_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "192.168.1.99", "port": 502, CONF_SLAVE: 1}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert config_entry.data == ENTRY_DATA


@pytest.mark.usefixtures("modbus")
async def test_user_flow_refuses_a_host_an_entry_was_moved_to(
    hass: HomeAssistant,
) -> None:
    MockConfigEntry(
        domain=DOMAIN, unique_id="192.168.1.2", data={**ENTRY_DATA, "host": HOST}
    ).add_to_hass(hass)

    result = await _submit(hass, {"host": HOST})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
