"""binary_sensor 平台：注册门锁低电量传感器。"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity.battery import KiwiLockBattery


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """注册低电量传感器实体。"""
    entities = hass.data[DOMAIN][entry.entry_id].get("entities", [])
    binary_entities = [
        entity for entity in entities if isinstance(entity, KiwiLockBattery)
    ]

    if binary_entities:
        async_add_entities(binary_entities, True)
