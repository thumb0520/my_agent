import anyio
import click
import mcp.types as types
from mcp.server import Server
from pydantic import Field
import os
from dotenv import load_dotenv
import json
import httpx

load_dotenv()
TAVILY_SEARCH_API_KEY = os.getenv("TAVILY_API_KEY")


async def fetch_website(
        question: str = Field(description="The search query string."),
        num_results: int = Field(description="The number of search results to return.")
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
           Search question in tavily Search API and return the searching results

           Args:
               question (`str`):
                   The search query string.
               num_results (`int`, defaults to `10`):
                   The number of search results to return.
           Returns:
               `content`. The `status` variable is from the ServiceExecStatus enum,
               and `content` is a list of search results or error information,
               which depends on the `status` variable.
               For each searching result, it is a dictionary with keys 'title',
               'link', and 'snippet'.

           Example:
               .. code-block:: python

                   results = tavily_search(question="What is an agent?",
                                        num_results=2)
                   print(results)

               It returns the following dict.

               .. code-block:: python

                    [
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
           """
    url = "https://api.tavily.com/search"
    authorization = f"Bearer {TAVILY_SEARCH_API_KEY}"
    payload = {
        "query": question,
        "topic": "general",
        "search_depth": "basic",
        "chunks_per_source": 3,
        "max_results": num_results,
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

    async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        json_data = json.loads(response.text)
        content = [
            {
                "title": result["title"],
                "link": result["url"],
                "snippet": result["content"],
            }
            for result in json_data["results"]
        ]
        return [types.TextContent(type="text", text=json.dumps(content, ensure_ascii=False))]


@click.command()
@click.option("--port", default=8000, help="Port to listen on for SSE")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type",
)
def main(port: int, transport: str) -> int:
    app = Server("mcp-website-fetcher")

    @app.call_tool()
    async def fetch_tool(
            name: str, arguments: dict
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        if name != "fetch":
            raise ValueError(f"Unknown tool: {name}")
        if "question" not in arguments or "num_results" not in arguments:
            raise ValueError("Missing required argument")
        return await fetch_website(arguments["question"], arguments["num_results"])

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="fetch",
                description="Fetches a website and returns its content",
                inputSchema={
                    "type": "object",
                    "required": ["url"],
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The search query string.",
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "The number of results to return.",
                        }
                    },
                },
            )
        ]

    if transport == "sse":
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(
                    request.scope, request.receive, request._send
            ) as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )
                return None  # Explicitly return None to indicate successful completion

        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )

        import uvicorn

        uvicorn.run(starlette_app, host="127.0.0.1", port=port)
    else:
        from mcp.server.stdio import stdio_server

        async def arun():
            async with stdio_server() as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )

        anyio.run(arun)

    return 0


if __name__ == '__main__':
    main()
