"""KiwiOT Binary Sensor implementation."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import KiwiLockEvent

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KiwiOT binary sensors."""
    # 获取之前存储的实体
    entities = hass.data[DOMAIN].get(entry.entry_id, {}).get("entities", [])
    binary_sensor_entities = [
        entity for entity in entities 
        if isinstance(entity, KiwiLockEvent)
    ]
    
    if binary_sensor_entities:
        async_add_entities(binary_sensor_entities, True)