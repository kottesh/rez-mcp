from fastmcp import FastMCP
from tools.setup import login, logout, get_profile
from tools.results import get_results, get_result, download_result
from tools.hallticket import get_halltickets, download_hallticket
from config import REZConfig
from manager import rez_app, rez_lifespan, sessions
from starlette.applications import Starlette
from starlette.routing import Mount
from contextlib import asynccontextmanager, AsyncExitStack
import logging
from fastmcp.server.middleware import Middleware, MiddlewareContext
from datetime import datetime, timedelta
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuthMiddleware(Middleware):
    async def on_call_tool(self, mctx: MiddlewareContext, call_next):
        if mctx.message.name != "login":
            session_id = mctx.fastmcp_context.session_id
            session = sessions.get(session_id)

            if session is None:
                logger.info(f"User not logged in. Session ID: {session_id}")
                raise Exception("User not logged in, login to continue.")

            now = datetime.now()
            expires_at = session.expiresAt
            if now > expires_at:
                del sessions[session_id]  # remove if the session is expired.
                logger.info(
                    f"Removing Session({session_id}) expired at {expires_at.strftime('%Y-%m-%d %H:%M:%S')} | Register No: {session.register_no}"
                )
                raise Exception("Session expired, make a relogin request to continue.")
            elif expires_at - now <= timedelta(minutes=5):
                new_expiry = expires_at + timedelta(
                    minutes=10
                )  # if the session is gonna end in 5 minutes add +10 mins
                logger.info(
                    f"Extending Session({session_id} from {expires_at.strftime('%Y-%m-%d %H:%M:%S')} -> {new_expiry.strftime('%Y-%m-%d %H:%M:%S')})"
                )
                sessions[session_id].expiresAt = new_expiry

            mctx.fastmcp_context.set_state("session", session)

        response = await call_next(mctx)
        return response


def main():
    mcp = FastMCP(name="Rez MCP Server")
    mcp.add_middleware(AuthMiddleware())

    mcp.tool(login)
    mcp.tool(logout)
    mcp.tool(get_profile)
    mcp.tool(get_results)
    mcp.tool(get_result)
    mcp.tool(download_result)
    mcp.tool(get_halltickets)
    mcp.tool(download_hallticket)

    rez_mcp = mcp.http_app(path="/mcp", transport="streamable-http")
    rez_mcp_lifespan = rez_mcp.lifespan

    @asynccontextmanager
    async def lifespan(app):
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(rez_mcp_lifespan(app))
            await stack.enter_async_context(rez_lifespan(app))
            yield

    app = Starlette(
        routes=[Mount("/rez", app=rez_mcp), Mount("/", app=rez_app)], lifespan=lifespan
    )

    uvicorn.run(app, host=REZConfig.REZ_HOST, port=REZConfig.REZ_PORT)


if __name__ == "__main__":
    main()
