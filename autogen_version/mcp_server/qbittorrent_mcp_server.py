import json
import logging
import mcp.types as types
from pydantic import Field
import os
from dotenv import load_dotenv
from typing import List
from fastmcp import FastMCP
from qbittorrentapi import Client
from autogen_version.rarbg import rarbgcli
from autogen_version.config.mcp_server_config import QBITTORRENT_MCP_SERVER_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()
mcp = FastMCP("qbittorrent_mcp_server")

qb_host = os.getenv("QBITTORRENTAPI_HOST")
qb_port = os.getenv("QBITTORRENTAPI_PORT")
qb_user = os.getenv("QBITTORRENTAPI_USERNAME")
qb_password = os.getenv("QBITTORRENTAPI_PASSWORD")


async def getClient():
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
async def add_download_url(
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
    client = await getClient()
    result = client.torrents_add(url)
    logger.info(f"Successfully added torrents: {result}")
    return [types.TextContent(type="text", text=result)]


@mcp.tool
async def get_download_url(
        query: str = Field(description="The search query movie name ")
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
           find magnet download url from rarbg.
           Normally, search results display the magnet download url with the largest file size.
           We might enable customizable parameters in the future to display magnet download url based on alternative sorting criteria.

           Args:
               query (`str`):
                   The query movie name. The query name must be English.
           Returns:
               `magnet_url`. If rarbg db contains the movie,it will show the magnet url in the result.
               Otherwise, it will be a empty list.


           Example:
               .. code-block:: python

                   results = get_download_url(query="Before Sunrise")
                   print(results)

               It returns the following string.

               .. code-block:: python

                    [
                        {
                            "magnet_url":"magnet:?xt=urn:btih:8094D7EA2D291AB2571004E7B56E457710FBE7E6&dn=Before.Sunrise.1995.Criterion.1080p.Remux.Bluray.FLAC.h264-LAA"
                        }
                    ]
    """
    logger.info(f"Searching for movie: {query}")
    args = [
        query,
        "--magnet",
        "--category", "movies",
        "--order", "size",
        "--limit", "1"
    ]
    result = rarbgcli.cli(args)
    logger.info(f"Found {len(result)} results for query: {query}")
    return [
        types.TextContent(
            type="text", text=json.dumps([{"magnet_url": t} for t in result], ensure_ascii=False)
        )
    ]


if __name__ == "__main__":
    logger.info("Starting qBittorrent MCP server")
    transport, port = QBITTORRENT_MCP_SERVER_CONFIG["transport"], QBITTORRENT_MCP_SERVER_CONFIG["port"]
    mcp.run(transport=transport, port=port)
