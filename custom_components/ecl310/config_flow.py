"""Config flow for Danfoss ECL 310."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_SLAVE, DEFAULT_PORT, DEFAULT_SLAVE, DOMAIN
from .ecl310 import ECL310Device

_HOST_RE = re.compile(
    r"^(\d{1,3}\.){3}\d{1,3}$"  # IPv4
    r"|^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$"  # hostname
    r"|^localhost$"
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
        vol.Optional(CONF_SLAVE, default=DEFAULT_SLAVE): vol.Coerce(int),
    }
)


class CannotConnect(HomeAssistantError):
    """Raised when connection to the device fails."""


class InvalidHost(HomeAssistantError):
    """Raised when the host string is not a valid IP or hostname."""


class ECL310ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for ECL 310."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host: str = user_input[CONF_HOST].strip()
            port: int = user_input[CONF_PORT]
            slave: int = user_input[CONF_SLAVE]

            try:
                if not _HOST_RE.match(host):
                    raise InvalidHost
                await _test_connection(host, port, slave)
            except InvalidHost:
                errors["host"] = "invalid_host"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"ECL 310 ({host})",
                    data={CONF_HOST: host, CONF_PORT: port, CONF_SLAVE: slave},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )


async def _test_connection(host: str, port: int, slave: int) -> None:
    """Attempt a connection and a single register read."""
    device = ECL310Device(host=host, port=port, slave=slave)
    try:
        await device.async_connect()
    except Exception as err:
        raise CannotConnect from err
    finally:
        await device.async_close()
