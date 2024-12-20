import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_IDENTIFIER, CONF_CREDENTIAL, CONF_CLIENT_ID

class KiwiOTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KiwiOT."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """处理初始步骤。"""
        errors = {}

        if user_input is not None:
            if len(user_input[CONF_IDENTIFIER]) < 3:
                errors[CONF_IDENTIFIER] = "identifier_too_short"
            else:
                return self.async_create_entry(title="KiwiOT", data=user_input)

        # 定义数据模式
        data_schema = vol.Schema({
            vol.Required(CONF_IDENTIFIER): str,  
            vol.Required(CONF_CREDENTIAL): str,  
            vol.Required(CONF_CLIENT_ID): str, 
        })

        # 显示表单并返回
        return self.async_show_form(
            step_id="user",  
            data_schema=data_schema,  
            errors=errors,  
        )