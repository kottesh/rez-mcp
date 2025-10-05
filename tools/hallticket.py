from fastmcp import Context
from utils import call
from bs4 import BeautifulSoup
from pydantic import Field
from config import rez_config


async def get_halltickets(ctx: Context) -> list[str]:
    """
    Retrieves a list of available halltickets code

    Returns:
        list: List of halltickets code

    Raises:
        Exception: If the user is not logged in or API call fails
    """

    session = ctx.get_state("session")
    response = await call(
        "/exam/param_exam_hallticket.php", addtional_headers={"Cookie": session.cookie}
    )
    sp = BeautifulSoup(response, "html.parser")

    input_tags = sp.find_all("input", {"id": "exam_cd"})
    halltickets = list(set(map(lambda tag: tag.get("value"), input_tags)))

    return halltickets


async def download_hallticket(
    ctx: Context,
    exam_code: str = Field(
        ..., description="Hallticket exam_code, can be get from get_halltickets tool."
    ),
) -> str:
    """
    Generates Hallticket PDF by `exam_code`

    Returns:
        str: Downloadable Hallticket PDF link.

    Rasies:
        Exception: If the user is not found or if the API calls.
    """

    session = ctx.get_state("session")
    return f"[Click here to download hallticket]({rez_config.rez_base_url}/pdf/hallticket?session_id={session.session_id}&exam_code={exam_code})"
