from fastmcp import Context
from utils import call
from bs4 import BeautifulSoup
from pydantic import Field
from config import REZConfig
from signer import generate_token
import logging

logger = logging.getLogger(__name__)


async def get_halltickets(ctx: Context) -> list[str] | str:
    """
    Retrieves a list of available halltickets code

    Returns:
        list: List of halltickets code

    Raises:
        Exception: If the user is not logged in or API call fails
    """

    session = ctx.get_state("session")
    logger.info(
        f"`get_halltickets` tool called with Session id {session.session_id} | Register No: {session.register_no}"
    )

    response = await call(
        "/exam/param_exam_hallticket.php", addtional_headers={"Cookie": session.cookie}
    )
    sp = BeautifulSoup(response, "html.parser")

    input_tags = sp.find_all("input", {"id": "exam_cd"})
    exam_codes = [
        set(exam_code for tag in input_tags if (exam_code := tag.get("value", "").strip()))
    ]

    if not exam_codes:
        logger.info(f"No halltickets are available | Session ID: {session.session_id}")
        return "Currently no halltickets are available."

    return exam_codes


async def download_hallticket(
    ctx: Context,
    exam_code: str = Field(
        ..., description="Hallticket exam_code, can be get from get_halltickets tool."
    ),
) -> str:
    """
    Generates Hallticket PDF by `exam_code`

    Returns:
        str: Downloadable Hallticket PDF link.(Valid only for 10 minutes)

    Rasies:
        Exception: If the user is not found or if the API calls.
    """

    session = ctx.get_state("session")
    logger.info(
        f"`download_hallticket` tool called with Session id {session.session_id} | Register No: {session.register_no}"
    )

    response = await call(
        "/exam/param_exam_hallticket.php", addtional_headers={"Cookie": session.cookie}
    )
    sp = BeautifulSoup(response, "html.parser")

    input_tags = sp.find_all("input", {"id": "exam_cd"})
    exam_codes = [
        exam_code for tag in input_tags if (exam_code := tag.get("value", "").strip())
    ]

    if not exam_codes:
        logger.info(f"No halltickets are available | Session ID: {session.session_id}")
        return "Currently no halltickets are available."

    token = generate_token(f"{session.session_id}:{exam_code}")
    logger.info(
        f"Hallticket download token generated | Session ID: {session.session_id} | Register No: {session.register_no}"
    )

    return f"[Click here to download hallticket]({REZConfig.REZ_BASE_URL}/pdf/hallticket?token={token})"
