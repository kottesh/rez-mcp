from fastmcp import FastMCP
import asyncio
from tools.setup import login, get_profile
from config import rez_config
from manager import app
import uvicorn

mcp = FastMCP(name="Rez MCP Server")

mcp.tool(login)
mcp.tool(get_profile)


async def run_manager():
    config = uvicorn.Config(
        app=app,
        host=rez_config.mcp_auth_host,
        port=rez_config.mcp_auth_port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def run_mcp():
    MCP_MODE = rez_config.mcp_mode
    if MCP_MODE == "stdio":
        await mcp.run_async(transport="stdio", show_banner=False)
    elif MCP_MODE == "http":
        await mcp.run_async(
            transport="http",
            host=rez_config.mcp_host,
            port=rez_config.mcp_port,
            show_banner=False,
        )


async def run_services():
    await asyncio.gather(run_manager(), run_mcp())


if __name__ == "__main__":
    asyncio.run(run_services())
