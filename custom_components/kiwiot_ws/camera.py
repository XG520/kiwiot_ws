﻿#from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity.lock import KiwiLockCamera

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    entities = hass.data[DOMAIN][entry.entry_id].get("entities", [])
    camera_entities = [
        entity for entity in entities 
        if isinstance(entity, KiwiLockCamera)
    ]
    
    if camera_entities:
        async_add_entities(camera_entities, True)