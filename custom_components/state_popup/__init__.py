from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import voluptuous as vol

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util
from homeassistant.components import websocket_api

from .const import (
    CONF_COOLDOWN,
    CONF_ENTITIES,
    CONF_EXCLUDE_DOMAINS,
    CONF_INCLUDE_DOMAINS,
    CONF_BACKGROUND_URL,
    CONF_TEXT_COLOR,
    CONF_TEXT_POSITION,
    CONF_FONT_SIZE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_COOLDOWN = 2.0  # seconds per entity to avoid floods
DEFAULT_TEXT_COLOR = "#ffffff"
DEFAULT_FONT_SIZE = "16px"
DEFAULT_TEXT_POSITION = "center"  # center | top | bottom | etc.

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_ENTITIES, default=[]): vol.All(
                    cv.ensure_list, [cv.entity_id]
                ),
                vol.Optional(CONF_INCLUDE_DOMAINS, default=[]): vol.All(
                    cv.ensure_list, [cv.string]
                ),
                vol.Optional(CONF_EXCLUDE_DOMAINS, default=[]): vol.All(
                    cv.ensure_list, [cv.string]
                ),
                vol.Optional(CONF_COOLDOWN, default=DEFAULT_COOLDOWN): vol.All(
                    vol.Coerce(float), vol.Range(min=0)
                ),
                vol.Optional(CONF_BACKGROUND_URL): cv.url,
                vol.Optional(CONF_TEXT_COLOR, default=DEFAULT_TEXT_COLOR): cv.string,
                vol.Optional(CONF_TEXT_POSITION, default=DEFAULT_TEXT_POSITION): cv.string,
                vol.Optional(CONF_FONT_SIZE, default=DEFAULT_FONT_SIZE): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration via YAML."""
    cfg = config.get(DOMAIN, {})
    include_domains: list[str] = cfg.get(CONF_INCLUDE_DOMAINS, [])
    exclude_domains: list[str] = cfg.get(CONF_EXCLUDE_DOMAINS, [])
    entities: list[str] = cfg.get(CONF_ENTITIES, [])
    cooldown: float = cfg.get(CONF_COOLDOWN, DEFAULT_COOLDOWN)
    background_url: str | None = cfg.get(CONF_BACKGROUND_URL)
    text_color: str = cfg.get(CONF_TEXT_COLOR, DEFAULT_TEXT_COLOR)
    text_position: str = cfg.get(CONF_TEXT_POSITION, DEFAULT_TEXT_POSITION)
    font_size: str = cfg.get(CONF_FONT_SIZE, DEFAULT_FONT_SIZE)

    hass.data[DOMAIN] = {
        CONF_ENTITIES: set(entities),
        CONF_INCLUDE_DOMAINS: set(include_domains),
        CONF_EXCLUDE_DOMAINS: set(exclude_domains),
        CONF_COOLDOWN: cooldown,
        CONF_BACKGROUND_URL: background_url,
        CONF_TEXT_COLOR: text_color,
        CONF_TEXT_POSITION: text_position,
        CONF_FONT_SIZE: font_size,
        "last_sent": {},  # entity_id -> datetime
    }

    websocket_api.async_register_command(hass, _ws_subscribe)
    _LOGGER.debug(
        "state_popup configured; entities=%s include_domains=%s exclude_domains=%s cooldown=%s bg=%s",
        entities,
        include_domains,
        exclude_domains,
        cooldown,
        background_url,
    )
    return True


def _entity_allowed(hass: HomeAssistant, entity_id: str) -> bool:
    data = hass.data[DOMAIN]
    if data[CONF_ENTITIES] and entity_id not in data[CONF_ENTITIES]:
        return False
    domain = entity_id.split(".", 1)[0]
    if data[CONF_EXCLUDE_DOMAINS] and domain in data[CONF_EXCLUDE_DOMAINS]:
        return False
    if data[CONF_INCLUDE_DOMAINS] and domain not in data[CONF_INCLUDE_DOMAINS]:
        return False
    return True


def _cooldown_ok(hass: HomeAssistant, entity_id: str) -> bool:
    data = hass.data[DOMAIN]
    cooldown = data[CONF_COOLDOWN]
    if cooldown <= 0:
        return True
    last_sent: dict[str, Any] = data["last_sent"]
    now = dt_util.utcnow()
    last = last_sent.get(entity_id)
    if last and (now - last) < timedelta(seconds=cooldown):
        return False
    last_sent[entity_id] = now
    return True


@websocket_api.websocket_command({"type": f"{DOMAIN}/subscribe"})
@websocket_api.async_response
async def _ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
):
    """Subscribe a front-end to state change push messages."""

    @callback
    def handle_event(event):
        entity_id = event.data.get("entity_id")
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if not entity_id or not new_state:
            return
        if old_state and old_state.state == new_state.state:
            return
        if not _entity_allowed(hass, entity_id):
            return
        if not _cooldown_ok(hass, entity_id):
            return

        payload = {
            "entity_id": entity_id,
            "old": old_state.state if old_state else None,
            "new": new_state.state,
            "friendly_name": new_state.name,
            "last_changed": new_state.last_changed.isoformat(),
            "style": {
                "background_url": hass.data[DOMAIN].get(CONF_BACKGROUND_URL),
                "text_color": hass.data[DOMAIN].get(CONF_TEXT_COLOR),
                "text_position": hass.data[DOMAIN].get(CONF_TEXT_POSITION),
                "font_size": hass.data[DOMAIN].get(CONF_FONT_SIZE),
            },
        }
        connection.send_message(websocket_api.event_message(msg["id"], payload))

    remove = hass.bus.async_listen(EVENT_STATE_CHANGED, handle_event)
    connection.subscriptions[msg["id"]] = remove
    connection.send_message(websocket_api.result_message(msg["id"], {"ok": True}))
