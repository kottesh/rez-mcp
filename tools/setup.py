from fastmcp import Context
from manager import sessions
import logging
from config import REZConfig
from utils import call
from bs4 import BeautifulSoup
from signer import generate_token

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
        Login URL or confirms if the user is already logged in. (Valid for only 10 minutes.)
    """

    session_id = ctx.session_id

    logger.info(f"`login` tool called with Session id: {session_id}")

    if session_id in sessions:
        return "You are already logged in!"

    login_token = generate_token(session_id)

    logger.info(f"Login token generated | Session ID: {session_id}")

    return f"[Click here to login]({REZConfig.REZ_BASE_URL}/auth/login?token={login_token})"


async def logout(ctx: Context) -> str:
    """
    Logout the user by invalidating their session.

    Returns:
        str: Success or error message indicating logout status
    """

    session_id = ctx.session_id
    logger.info(f"`logout` tool called with Session id: {session_id}")

    if session_id not in sessions:
        logger.info(f"Logout failed. No session {session_id} found.")
        return "You aren't logged in to logout."

    del sessions[session_id]

    return "You are now logged out!"


async def get_profile(ctx: Context) -> dict:
    """
    Retrieves the student's profile information from the CIT results site.

    Returns:
        dict: A dictionary containing the student's profile information.

    Raises:
        Exception: If the user is not logged in or if the API call fails.
    """

    session = ctx.get_state("session")
    logger.info(
        f"`get_profile` tool called with Session id {session.session_id} | Register No: {session.register_no}"
    )

    data = await call("/personal.php", addtional_headers={"Cookie": session.cookie})

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
