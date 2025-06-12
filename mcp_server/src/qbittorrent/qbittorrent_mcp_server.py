import logging
import mcp.types as types
from pydantic import Field
from dotenv import load_dotenv
from typing import List
from fastmcp import FastMCP
from qbittorrentapi import Client
from config.mcp_server_config import QBITTORRENT_MCP_SERVER_CONFIG
from config.env_config import env_config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

mcp = FastMCP("qbittorrent_mcp_server")

qb_host = env_config.get("QBITTORRENTAPI_HOST")
qb_port = env_config.get("QBITTORRENTAPI_PORT")
qb_user = env_config.get("QBITTORRENTAPI_USERNAME")
qb_password = env_config.get("QBITTORRENTAPI_PASSWORD")


def getClient():
    logger.info("Initializing qBittorrent client")
    # 创建Client对象
    client = Client(
        host=qb_host,  # qBittorrent的地址，可以是IP或主机名
        port=qb_port,  # qBittorrent的Web API端口，默认是8080
        username=qb_user,  # 你的用户名，如果没有设置则可以省略或使用None
        password=qb_password  # 你的密码，如果没有设置则可以省略或使用None
    )
    logger.debug(f"Client initialized with host: {qb_host}, port: {qb_port}")
    return client


@mcp.tool
def add_download_url(
        url: List[str] = Field(description="the qb download url list")
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
           add download url to qbittorrent download list

           Args:
               url (`List[str]`):
                   The download url list
           Returns:
               ``Ok.`` for success and ``Fails.`` for failure.


           Example:
               .. code-block:: python

                   results = add_download_url(download_urls=["magnet:?xt=urn:btih:SOME_HASH_CODE"])
                   print(results)

               It returns the following string.

               .. code-block:: python

                    "OK."
    """
    logger.info(f"Adding download URLs: {url}")
    client = getClient()
    result = client.torrents_add(url)
    logger.info(f"Successfully added torrents: {result}")
    return [types.TextContent(type="text", text=result)]


class QbittorrentMCPServer:
    def __init__(self):
        load_dotenv()
        self.mcp = mcp

    def run(self):
        logger.info("Starting qbittorrent operation MCP server")
        run_config = QBITTORRENT_MCP_SERVER_CONFIG
        transport, port = run_config["transport"], run_config["port"]
        mcp.run(transport=transport, port=port)


if __name__ == "__main__":
    QbittorrentMCPServer().run()
