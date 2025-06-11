QBITTORRENT_MCP_SERVER_CONFIG = {
    "port": 8081,
    "transport": "sse"
}

WEB_SEARCH_MCP_SERVER_CONFIG = {
    "port": 8080,
    "transport": "sse"
}


def valid():
    return True


def get_default_address(config):
    if not valid():
        return ""
    if config["transport"] == "sse":
        return f"http://127.0.0.1:{config['port']}/sse"
    return ""