import json
import logging
import mcp.types as types
from pydantic import Field
from dotenv import load_dotenv
from fastmcp import FastMCP
from rarbg import rarbgcli
from config.mcp_server_config import MAGNET_SEARCH_MCP_SERVER_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
mcp = FastMCP("magnet_search_mcp_server")


@mcp.tool
def get_download_url(
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
               list[str]. If rarbg db contains the movie,it will show the magnet url in the result.


           Example:
               .. code-block:: python

                   results = get_download_url(query="Before Sunrise")
                   print(results)

               It returns the following string.

               .. code-block:: python

                    [
                        "magnet:?xt=urn:btih:8094D7EA2D291AB2571004E7B56E457710FBE7E6&dn=Before.Sunrise.1995.Criterion.1080p.Remux.Bluray.FLAC.h264-LAA"
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
            type="text", text=json.dumps(result, ensure_ascii=False)
        )
    ]


class MagnetSearchMcpServer:
    def __init__(self):
        load_dotenv()
        self.mcp = mcp

    def run(self):
        logger.info("Starting magnet search MCP server")
        run_config = MAGNET_SEARCH_MCP_SERVER_CONFIG
        transport, port = run_config["transport"], run_config["port"]
        self.mcp.run(transport=transport, port=port)


if __name__ == "__main__":
    MagnetSearchMcpServer().run()
