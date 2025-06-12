from .env_config import env_config


def get_config_with_env(port_key: str, transport_key: str, default_port: int, default_transport: str) -> dict:
    return {
        "port": int(env_config.get(port_key, str(default_port))),
        "transport": env_config.get(transport_key, default_transport)
    }


QBITTORRENT_MCP_SERVER_CONFIG = get_config_with_env(
    "QBITTORRENT_PORT",
    "QBITTORRENT_TRANSPORT",
    8081,
    "sse"
)

MAGNET_SEARCH_MCP_SERVER_CONFIG = get_config_with_env(
    "MAGNET_SEARCH_PORT",
    "MAGNET_SEARCH_TRANSPORT",
    8082,
    "sse"
)

WEB_SEARCH_MCP_SERVER_CONFIG = get_config_with_env(
    "WEB_SEARCH_PORT",
    "WEB_SEARCH_TRANSPORT",
    8080,
    "sse"
)


def valid():
    return True


def get_default_address(config):
    if not valid():
        return ""
    if config["transport"] == "sse":
        return f"http://127.0.0.1:{config['port']}/sse"
    return ""
