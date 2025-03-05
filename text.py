"""Text platform for kiwiot_ws integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity.lock import KiwiLockUser
from .entity.lock_ctrl import KiwiLockPasswordInput

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up text entities."""
    entities = hass.data[DOMAIN][entry.entry_id].get("entities", [])
    text_entities = [
        entity for entity in entities 
        if isinstance(entity, (KiwiLockUser, KiwiLockPasswordInput))
    ]
    
    if text_entities:
        async_add_entities(text_entities, True)