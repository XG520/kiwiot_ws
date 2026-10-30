import voluptuous as vol
import aiohttp
from homeassistant import config_entries
from typing import Any, Dict, Optional
from .const import DOMAIN, CONF_IDENTIFIER, CONF_CREDENTIAL, CONF_CLIENT_ID, CONF_IGNORE_SSL, BASE_URL


def _build_schema(defaults: Optional[Dict] = None) -> vol.Schema:
    """构建配置表单 schema（可带默认值预填）"""
    defaults = defaults or {}
    return vol.Schema({
        vol.Required(CONF_IDENTIFIER, default=defaults.get(CONF_IDENTIFIER, "+86")): str,
        vol.Required(CONF_CREDENTIAL, default=defaults.get(CONF_CREDENTIAL, "")): str,
        vol.Required(CONF_CLIENT_ID, default=defaults.get(CONF_CLIENT_ID, "")): str,
        vol.Optional(CONF_IGNORE_SSL, default=defaults.get(CONF_IGNORE_SSL, False)): bool,
    })


async def _validate_credentials(identifier: str, credential: str, client_id: str, ignore_ssl: bool) -> bool:
    """用账号密码请求 token，验证凭据是否正确"""
    headers = {"X-Kiwik-Client-Id": client_id}
    data = {
        "identifier": identifier,
        "credential": credential,
        "auth_type": "password"
    }
    timeout = aiohttp.ClientTimeout(total=15, connect=10)
    connector = aiohttp.TCPConnector(ssl=not ignore_ssl)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        async with session.post(
            f"{BASE_URL}/restapi/auth/tokens",
            headers=headers,
            json=data,
        ) as response:
            return response.status == 201


class KiwiOTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        errors = {}

        if user_input is not None:
            identifier = user_input.get(CONF_IDENTIFIER)
            credential = user_input.get(CONF_CREDENTIAL)
            client_id = user_input.get(CONF_CLIENT_ID)
            ignore_ssl = user_input.get(CONF_IGNORE_SSL, False)

            if not isinstance(identifier, str):
                 errors["identifier"] = "identifier_invalid_format"
            elif not all([identifier, credential, client_id]):
                errors["base"] = "missing_fields"
            else:
                # 先用账号密码验证一次，避免「添加成功却在设置阶段才报密码错」
                try:
                    if await _validate_credentials(identifier, credential, client_id, ignore_ssl):
                        return self.async_create_entry(title="KiwiOT", data=user_input)
                    errors["base"] = "invalid_auth"
                except Exception:
                    errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(user_input),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return KiwiOTOptionsFlow()


class KiwiOTOptionsFlow(config_entries.OptionsFlow):
    """选项流程：集成卡片 ⋮ 左侧的齿轮按钮入口"""

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None):
        entry = self.config_entry
        errors = {}

        if user_input is not None:
            identifier = user_input.get(CONF_IDENTIFIER)
            credential = user_input.get(CONF_CREDENTIAL)
            client_id = user_input.get(CONF_CLIENT_ID)
            ignore_ssl = user_input.get(CONF_IGNORE_SSL, False)

            if not all([identifier, credential, client_id]):
                errors["base"] = "missing_fields"
            else:
                try:
                    if await _validate_credentials(identifier, credential, client_id, ignore_ssl):
                        self.hass.config_entries.async_update_entry(entry, data=user_input)
                        await self.hass.config_entries.async_reload(entry.entry_id)
                        return self.async_abort(reason="reconfigure_successful")
                    errors["base"] = "invalid_auth"
                except Exception:
                    errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(dict(entry.data)),
            errors=errors,
        )
