from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import KiwiLockUser, KiwiLockInfo, KiwiLockStatus
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置传感器实体"""
    entities = hass.data[DOMAIN][entry.entry_id].get("entities", [])
    sensor_entities = [
        entity for entity in entities 
        if isinstance(entity, (KiwiLockInfo, KiwiLockStatus, KiwiLockUser))
    ]
    
    if sensor_entities:
        async_add_entities(sensor_entities, True)