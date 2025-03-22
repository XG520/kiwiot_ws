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
WS_URL= "wss://wsapi.kiwiot.com"
TOKEN_EXPIRATION_BUFFER = 300 
STORAGE_VERSION = 1
STORAGE_KEY = "kiwiot_tokens"


# 日志
LOGGER_NAME = f"{DOMAIN}_logger"