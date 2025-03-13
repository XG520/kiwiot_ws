DOMAIN = "kiwiot_ws"

CONF_IDENTIFIER = "identifier"
CONF_CREDENTIAL = "credential"
CONF_CLIENT_ID = "X-Kiwik-Client-Id"
CONF_ACCESS_TOKEN = "access_token"
CONF_IGNORE_SSL = "ignore_ssl"

# 实体类别
DEVICE_TYPES = {
    "LOCK": "Smart Lock",
}

ENTITY_TYPES = {
    "STATUS": "Status",
    "BATTERY": "Battery",
    "USER": "User",
}

# API 地址
BASE_URL = "https://h5.kiwik.cn"
AUTH_URL = "https://h5.kiwik.cn/restapi/auth/tokens"
WS_URL= "wss://wsapi.kiwiot.com"

# 日志
LOGGER_NAME = f"{DOMAIN}_logger"