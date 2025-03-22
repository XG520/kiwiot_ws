from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity.lock_ctrl import KiwiLockPasswordConfirm

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    entities = hass.data[DOMAIN][entry.entry_id].get("entities", [])
    button_entities = [
        entity for entity in entities 
        if isinstance(entity, KiwiLockPasswordConfirm)
    ]
    
    if button_entities:
        async_add_entities(button_entities, True)