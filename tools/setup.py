from fastmcp import Context
from manager import sessions
import logging
from config import rez_config
from utils import call
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


async def login(ctx: Context) -> str:
    """
    Initiates the user login process for the CIT Results Site.

    This tool must be called before any other tool if the user is not already authenticated.
    It generates a unique login URL that must be presented to the user. The user needs to
    visit this URL in their browser to complete the authentication process.

    If the user is already logged in, this tool will confirm their authenticated status.

    Command:
        Show the login URL in a markdown format

    Returns:
        Login URL or confirms if the user is already logged in.
    """

    mcp_session_id = ctx.session_id

    logger.info(f"Login tool called with mcp session id {mcp_session_id}")

    if sessions.get(mcp_session_id) is not None:
        return "You are already logged in!"

    sessions[mcp_session_id] = None

    return f"Follow the link to login: http://{rez_config.mcp_auth_host}:{rez_config.mcp_auth_port}/auth/login?session_id={mcp_session_id}"


async def get_profile(ctx: Context) -> dict:
    """
    Retrieves the student's profile information from the CIT results site.

    Returns:
        dict: A dictionary containing the student's profile information.

    Raises:
        Exception: If the user is not logged in or if the API call fails.
    """

    session_id = ctx.session_id
    if sessions.get(session_id) is None:
        raise Exception("User not logged in, login to continue.")

    data = await call(
        "/personal.php", addtional_headers={"Cookie": sessions[session_id].cookie}
    )

    sp = BeautifulSoup(data, "html.parser")
    tables = sp.find("td", attrs={"align": "center"}).parent.find_all("table")
    tables = list(
        map(
            lambda table: [
                tr.td.string.strip() if tr.td.string else None
                for tr in table.find_all("tr")
            ],
            tables,
        )
    )

    profile = {k: v for k, v in zip(tables[0], tables[1])}

    return profile
