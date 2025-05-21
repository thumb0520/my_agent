import mcp.types as types
from pydantic import Field
import os
from dotenv import load_dotenv
import json
import httpx
from fastmcp import FastMCP

load_dotenv()
TAVILY_SEARCH_API_KEY = os.getenv("TAVILY_API_KEY")

mcp = FastMCP("tavily search server")

@mcp.tool()
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


if __name__ == "__main__":
    mcp.run(transport="sse")