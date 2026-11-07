"""Config and options flow of the ECL 310 integration."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
