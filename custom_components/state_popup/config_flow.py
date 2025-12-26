from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BACKGROUND_URL,
    CONF_COOLDOWN,
    CONF_ENTITIES,
    CONF_EXCLUDE_DOMAINS,
    CONF_FONT_SIZE,
    CONF_INCLUDE_DOMAINS,
    CONF_TEXT_COLOR,
    CONF_TEXT_POSITION,
    DEFAULT_COOLDOWN,
    DEFAULT_FONT_SIZE,
    DEFAULT_TEXT_COLOR,
    DEFAULT_TEXT_POSITION,
    DOMAIN,
)


def build_schema(defaults: dict[str, object]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_ENTITIES, default=defaults.get(CONF_ENTITIES, [])
            ): selector.EntitySelector(
                {"multiple": True}
            ),
            vol.Optional(
                CONF_INCLUDE_DOMAINS, default=defaults.get(CONF_INCLUDE_DOMAINS, [])
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[],
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    custom_value=True,
                )
            ),
            vol.Optional(
                CONF_EXCLUDE_DOMAINS, default=defaults.get(CONF_EXCLUDE_DOMAINS, [])
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[],
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    custom_value=True,
                )
            ),
            vol.Optional(
                CONF_COOLDOWN, default=defaults.get(CONF_COOLDOWN, DEFAULT_COOLDOWN)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=120, step=0.5, mode="box")
            ),
            vol.Optional(
                CONF_BACKGROUND_URL, default=defaults.get(CONF_BACKGROUND_URL, "")
            ): selector.TextSelector(),
            vol.Optional(
                CONF_TEXT_COLOR, default=defaults.get(CONF_TEXT_COLOR, DEFAULT_TEXT_COLOR)
            ): selector.TextSelector(),
            vol.Optional(
                CONF_TEXT_POSITION,
                default=defaults.get(CONF_TEXT_POSITION, DEFAULT_TEXT_POSITION),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["top", "center", "bottom"],
                    multiple=False,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_FONT_SIZE, default=defaults.get(CONF_FONT_SIZE, DEFAULT_FONT_SIZE)
            ): selector.TextSelector(),
        }
    )


class StatePopupConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for State Popup."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="State Popup", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=build_schema({}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return StatePopupOptionsFlow(config_entry)


class StatePopupOptionsFlow(config_entries.OptionsFlow):
    """Handle options for State Popup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=build_schema(defaults),
        )
