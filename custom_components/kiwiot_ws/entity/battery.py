"""门锁低电量传感器实体。

KiwiOT 云端只推送 LOW_BATTERY 事件（无电量数值、无恢复事件），
因此本传感器按「事件驱动 + 静默自愈」设计：
- 收到 LOW_BATTERY 事件 -> 置为开（电量不足）；
- 超过静默期无新的 LOW_BATTERY 上报 -> 自动恢复为关（推定已换电池）。
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.restore_state import RestoreEntity

from ..const import DOMAIN, LOGGER_NAME

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")

# 换电池后云端无「电量恢复」事件，超过该静默期无低电量上报即自动恢复
RECOVERY_SILENCE = timedelta(hours=36)
CHECK_INTERVAL = timedelta(hours=6)

SHANGHAI = ZoneInfo("Asia/Shanghai")


class KiwiLockBattery(BinarySensorEntity, RestoreEntity):
    """低电量传感器：收到 LOW_BATTERY 事件置为开。"""

    def __init__(self, hass, device, events):
        self.hass = hass
        self._device = device
        self._events = events or []
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{DOMAIN}_{device.device_id}_battery"
        self._attr_name = "电池"
        self._attr_device_class = BinarySensorDeviceClass.BATTERY
        self._attr_should_poll = False
        self._attr_is_on = False
        self._last_low_battery = None  # 最后低电量事件时间（UTC aware）
        self._event_id = None
        self._update_task = None
        self._restore_last_time = None  # HA 重启恢复时暂存的时间字符串
        # 从历史事件列表计算初始状态
        self._init_from_history()

    def _init_from_history(self):
        """从事件列表找最新 LOW_BATTERY，判断初始状态。"""
        for event in self._events:
            if event.get("name") != "LOW_BATTERY":
                continue
            created = event.get("created_at", "")
            try:
                ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue
            self._last_low_battery = ts
            self._event_id = event.get("id")
            break
        if self._last_low_battery:
            elapsed = datetime.now(timezone.utc) - self._last_low_battery
            self._attr_is_on = elapsed < RECOVERY_SILENCE

    @property
    def device_info(self):
        """返回设备信息"""
        return self._device.get_device_info()

    @property
    def extra_state_attributes(self):
        """返回额外的状态属性"""
        last_time = self._last_low_battery
        if last_time:
            shown = last_time.astimezone(SHANGHAI).strftime("%Y-%m-%d %H:%M:%S")
        else:
            shown = self._restore_last_time or "无"
        return {
            "最后低电量时间": shown,
            "事件ID": self._event_id or "无",
        }

    def update_from_event(self, event_data):
        """处理设备事件：LOW_BATTERY 置开并记录时间。"""
        if event_data.get("name") != "LOW_BATTERY":
            return
        created = event_data.get("created_at", "")
        try:
            ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            ts = datetime.now(timezone.utc)
        self._last_low_battery = ts
        self._event_id = event_data.get("id")
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """实体注册后恢复历史状态并启动自愈检查。"""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            self._attr_is_on = last.state == "on"
            if self._last_low_battery is None and last.attributes.get("最后低电量时间"):
                self._restore_last_time = last.attributes.get("最后低电量时间")
        self._update_task = self.hass.loop.create_task(self._recovery_check())

    async def async_will_remove_from_hass(self):
        """卸载时取消自愈检查任务。"""
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

    async def _recovery_check(self):
        """周期自愈：静默期无新低电量事件则自动恢复为正常。"""
        try:
            while True:
                await asyncio.sleep(CHECK_INTERVAL.total_seconds())
                if not (self._attr_is_on and self._last_low_battery):
                    continue
                if datetime.now(timezone.utc) - self._last_low_battery >= RECOVERY_SILENCE:
                    _LOGGER.info(
                        "设备 %s 已超过 %.0f 小时无低电量上报，自动恢复电量正常",
                        self._device.device_id,
                        RECOVERY_SILENCE.total_seconds() / 3600,
                    )
                    self._attr_is_on = False
                    self.async_write_ha_state()
        except asyncio.CancelledError:
            _LOGGER.info("电池传感器自愈检查任务已取消")
            raise
