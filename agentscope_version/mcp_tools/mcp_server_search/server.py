import logging
from pathlib import Path
from typing import Sequence, Any, Coroutine
from agentscope.service import ServiceResponse
from mcp.server import Server
from mcp.server.session import ServerSession
from mcp.server.stdio import stdio_server
from agentscope.service.service_response import ServiceResponse
from mcp.types import (
    ClientCapabilities,
    TextContent,
    Tool,
    ListRootsResult,
    RootsCapability,
)
from enum import Enum
from dotenv import load_dotenv
import requests
import json
from typing import Any
from agentscope.service.service_response import ServiceResponse
from agentscope.service.service_status import ServiceExecStatus
import requests
import json
from pydantic import BaseModel
import os

load_dotenv()
TAVILY_SEARCH_API_KEY = os.getenv("TAVILY_API_KEY")


class SearchTool(BaseModel):
    question: str
    num_results: int


class SearchTools(str, Enum):
    SEARCH = "search"


def search(question: str, num_results: int = 10):
    """
       Search question in tavily Search API and return the searching results

       Args:
           question (`str`):
               The search query string.
           api_key (`str`):
               The API key provided for authenticating with the tavily Search API.
           num_results (`int`, defaults to `10`):
               The number of search results to return.
           **kwargs (`Any`):
               Additional keyword arguments to be included in the search query.
               For more details, please refer to
               https://learn.microsoft.com/en-us/bing/search-apis/bing-web-search/reference/query-parameters

       Returns:
           `ServiceResponse`: A dictionary with two variables: `status` and
           `content`. The `status` variable is from the ServiceExecStatus enum,
           and `content` is a list of search results or error information,
           which depends on the `status` variable.
           For each searching result, it is a dictionary with keys 'title',
           'link', and 'snippet'.

       Example:
           .. code-block:: python

               results = tavily_search(question="What is an agent?",
                                    tavily_api_key="your api key",
                                    num_results=2,
                                    mkt="en-US")
               print(results)

           It returns the following dict.

           .. code-block:: python

               {
                   'status': <ServiceExecStatus.SUCCESS: 1>,
                   'content': [
                       {
                           'title': 'What Is an Agent? Definition, Types of
                               Agents, and Examples - Investopedia',
                           'link':
                           'https://www.investopedia.com/terms/a/agent.asp',
                           'snippet': "An agent is someone that is given
                               permission (either explicitly or assumed) to act
                               on an individual's behalf and may do so in a
                               variety of capacities. This could include
                               selling a home, executing..."},
                       {
                           'title': 'AGENT Definition & Usage Examples |
                                       Dictionary.com',
                           'link': 'https://www.dictionary.com/browse/agent',
                           'snippet': 'noun. a person who acts on behalf of
                               another person, group, business, government,
                               etc; representative. a person or thing that acts
                               or has the power to act. a phenomenon,
                               substance, or organism that exerts some force or
                               effect: a chemical agent.'
                       }
                   ]
               }
       """

    # tavily Search API endpoint
    url = "https://api.tavily.com/search"
    authorization = f"Bearer {TAVILY_SEARCH_API_KEY}"
    payload = {
        "query": question,
        "topic": "general",
        "search_depth": "basic",
        "chunks_per_source": 3,
        "max_results": 1,
        "time_range": None,
        "days": 7,
        "include_answer": True,
        "include_raw_content": False,
        "include_images": False,
        "include_image_descriptions": False,
        "include_domains": [],
        "exclude_domains": []
    }
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json"
    }

    response = requests.request("POST", url, json=payload, headers=headers)

    print(response.text)
    json_data = json.loads(response.text)
    content = [
        {
            "title": result["title"],
            "link": result["url"],
            "snippet": result["content"],
        }
        for result in json_data["results"]
    ]
    return ServiceResponse(
        status=ServiceExecStatus.SUCCESS,
        content=content,
    )


async def serve() -> None:
    server = Server("mcp_tools-search-server")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=SearchTools.SEARCH,
                description=" Search question in tavily Search API and return the searching results",
                inputSchema=SearchTool.model_json_schema(),
            ),

        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> ServiceResponse | None:
        match name:
            case SearchTools.SEARCH:
                question = arguments.get("question", "")
                num_results = arguments.get("num_results", 10)
                return search(question, num_results)
            case _:
                raise ValueError(f"Unknown tool: {name}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
