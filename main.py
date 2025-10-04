from fastmcp import FastMCP
from tools.setup import login, get_profile
from tools.results import get_results, get_result, download_result
from tools.hallticket import get_halltickets, download_hallticket
from manager import auth_app
from starlette.applications import Starlette
from starlette.routing import Mount

mcp = FastMCP(name="Rez MCP Server")

mcp.tool(login)
mcp.tool(get_profile)
mcp.tool(get_results)
mcp.tool(get_result)
mcp.tool(download_result)
mcp.tool(get_halltickets)
mcp.tool(download_hallticket)

mcp_app = mcp.http_app(path="/mcp", transport="streamable-http")

app = Starlette(
    routes=[Mount("/rez", app=mcp_app), Mount("/", app=auth_app)],
    lifespan=mcp_app.lifespan,
)
