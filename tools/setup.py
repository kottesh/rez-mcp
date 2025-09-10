from fastmcp import Context
from manager import sessions
import logging
from config import rez_config
from utils import call
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


async def login(ctx: Context) -> str:
    """
    While initiating a new conversation make sure to run this once, to ensure the user gets logged in.
    Use this tool to login to the CIT Results Site, If the session error occurs.
    It returns a Login URL represent it to the user in markdown embedded text.
    """

    mcp_session_id = ctx.session_id

    logger.info(f"Login tool called with mcp session id {mcp_session_id}")

    if sessions.get(mcp_session_id) is not None:
        return "You are already logged in!"

    sessions[mcp_session_id] = None

    return f"Follow the link to login: {rez_config.mcp_auth_host}:{rez_config.mcp_auth_port}/auth/login?session_id={mcp_session_id}"


async def get_profile(ctx: Context) -> dict:
    """
    Gets information about the student.

    Returns:
        dict: Response containing the student details.

    Raises:
        Exception: If the API call fails
    """

    if ctx.session_id not in sessions:
        raise Exception("User not logged in, login to continue.")

    data = await call("/personal.php")

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
