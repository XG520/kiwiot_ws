import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_IDENTIFIER, CONF_CREDENTIAL, CONF_CLIENT_ID, CONF_IGNORE_SSL

class KiwiOTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KiwiOT."""

    VERSION = 1.1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # 校验用户输入
            identifier = user_input.get(CONF_IDENTIFIER)
            credential = user_input.get(CONF_CREDENTIAL)
            client_id = user_input.get(CONF_CLIENT_ID)

            if not identifier.startswith("+86") or len(identifier) != 13:
                errors["identifier"] = "identifier_invalid_format"
            elif not all([identifier, credential, client_id]):
                errors["base"] = "missing_fields"
            else:
                return self.async_create_entry(title="KiwiOT", data=user_input)

        # 构建配置表单
        data_schema = vol.Schema({
            vol.Required(CONF_IDENTIFIER): str,
            vol.Required(CONF_CREDENTIAL): str,
            vol.Required(CONF_CLIENT_ID): str,
            vol.Optional(CONF_IGNORE_SSL, default=False): bool,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
