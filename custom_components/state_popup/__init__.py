from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util
from homeassistant.components import websocket_api
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)

from .const import (
    CONF_COOLDOWN,
    CONF_ENTITIES,
    CONF_EXCLUDE_DOMAINS,
    CONF_INCLUDE_DOMAINS,
    CONF_BACKGROUND_URL,
    CONF_TEXT_COLOR,
    CONF_TEXT_POSITION,
    CONF_FONT_SIZE,
    DEFAULT_COOLDOWN,
    DEFAULT_TEXT_COLOR,
    DEFAULT_TEXT_POSITION,
    DEFAULT_FONT_SIZE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _ensure_domain_data(hass: HomeAssistant) -> dict[str, Any]:
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"entries": {}, "ws_registered": False}
    return hass.data[DOMAIN]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration (no YAML config; config entry only)."""
    domain_data = _ensure_domain_data(hass)
    if not domain_data["ws_registered"]:
        websocket_api.async_register_command(hass, _ws_subscribe)
        domain_data["ws_registered"] = True
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from UI config entry."""
    domain_data = _ensure_domain_data(hass)
    cfg = _merge_config(entry)

    @callback
    def handle_event(event):
        _process_event(hass, entry.entry_id, cfg, event, domain_data)

    remove = hass.bus.async_listen(EVENT_STATE_CHANGED, handle_event)
    domain_data["entries"][entry.entry_id] = {
        "config": cfg,
        "last_sent": {},
        "unsub": remove,
    }
    _LOGGER.debug("state_popup entry %s configured: %s", entry.entry_id, cfg)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    domain_data = _ensure_domain_data(hass)
    data = domain_data["entries"].pop(entry.entry_id, None)
    if data and (unsub := data.get("unsub")):
        unsub()
    return True


def _merge_config(entry: ConfigEntry) -> dict[str, Any]:
    base = {
        CONF_ENTITIES: [],
        CONF_INCLUDE_DOMAINS: [],
        CONF_EXCLUDE_DOMAINS: [],
        CONF_COOLDOWN: DEFAULT_COOLDOWN,
        CONF_BACKGROUND_URL: None,
        CONF_TEXT_COLOR: DEFAULT_TEXT_COLOR,
        CONF_TEXT_POSITION: DEFAULT_TEXT_POSITION,
        CONF_FONT_SIZE: DEFAULT_FONT_SIZE,
    }
    merged = {**base, **entry.data, **entry.options}
    merged[CONF_ENTITIES] = merged.get(CONF_ENTITIES) or []
    merged[CONF_INCLUDE_DOMAINS] = merged.get(CONF_INCLUDE_DOMAINS) or []
    merged[CONF_EXCLUDE_DOMAINS] = merged.get(CONF_EXCLUDE_DOMAINS) or []
    return merged


def _get_active_entry(domain_data: dict[str, Any]) -> Optional[dict[str, Any]]:
    if not domain_data["entries"]:
        return None
    # pick the first entry
    entry_id, data = next(iter(domain_data["entries"].items()))
    return {"entry_id": entry_id, **data}


def _entity_allowed(cfg: dict[str, Any], entity_id: str) -> bool:
    entities = set(cfg.get(CONF_ENTITIES, []))
    include_domains = set(cfg.get(CONF_INCLUDE_DOMAINS, []))
    exclude_domains = set(cfg.get(CONF_EXCLUDE_DOMAINS, []))

    if entities and entity_id not in entities:
        return False
    domain = entity_id.split(".", 1)[0]
    if exclude_domains and domain in exclude_domains:
        return False
    if include_domains and domain not in include_domains:
        return False
    return True


def _cooldown_ok(last_sent: dict[str, Any], cooldown: float, entity_id: str) -> bool:
    if cooldown <= 0:
        return True
    now = dt_util.utcnow()
    last = last_sent.get(entity_id)
    if last and (now - last) < timedelta(seconds=cooldown):
        return False
    last_sent[entity_id] = now
    return True


def _process_event(
    hass: HomeAssistant,
    entry_id: str,
    cfg: dict[str, Any],
    event: Any,
    domain_data: dict[str, Any],
) -> None:
    entity_id = event.data.get("entity_id")
    old_state = event.data.get("old_state")
    new_state = event.data.get("new_state")
    if not entity_id or not new_state:
        return
    if old_state and old_state.state == new_state.state:
        return
    if not _entity_allowed(cfg, entity_id):
        return

    entry_data = domain_data["entries"].get(entry_id)
    if not entry_data:
        return
    last_sent = entry_data["last_sent"]
    if not _cooldown_ok(last_sent, cfg.get(CONF_COOLDOWN, DEFAULT_COOLDOWN), entity_id):
        return

    payload = {
        "entity_id": entity_id,
        "old": old_state.state if old_state else None,
        "new": new_state.state,
        "friendly_name": new_state.name,
        "last_changed": new_state.last_changed.isoformat(),
        "style": {
            "background_url": cfg.get(CONF_BACKGROUND_URL),
            "text_color": cfg.get(CONF_TEXT_COLOR, DEFAULT_TEXT_COLOR),
            "text_position": cfg.get(CONF_TEXT_POSITION, DEFAULT_TEXT_POSITION),
            "font_size": cfg.get(CONF_FONT_SIZE, DEFAULT_FONT_SIZE),
        },
    }
    # Push to all active WS subscribers for this command; HA handles per-connection.
    hass.components.websocket_api.async_dispatcher_send(
        f"{DOMAIN}_event", payload
    )


@websocket_api.websocket_command({"type": f"{DOMAIN}/subscribe"})
@websocket_api.async_response
async def _ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
):
    """Subscribe a front-end to state change push messages."""

    @callback
    def forward_event(payload):
        connection.send_message(websocket_api.event_message(msg["id"], payload))

    remove = hass.helpers.dispatcher.async_dispatcher_connect(
        f"{DOMAIN}_event", forward_event
    )
    connection.subscriptions[msg["id"]] = remove
    connection.send_message(websocket_api.result_message(msg["id"], {"ok": True}))
