from fastmcp import Context
from manager import sessions
import logging
from utils import call
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

async def get_results(ctx: Context) -> list:
    """
    Retrieves a list of available exam result codes from the CIT Results Site.

    This tool requires the user to be authenticated. If the user is not logged in,
    it will raise an exception, and the `login` tool must be called first.

    Returns:
        list: A list of the available exam result codes.

    Raises:
        Exception: If the user is not logged in or if the API call fails.
    """

    session_id = ctx.session_id
    if sessions.get(session_id) is None:
        raise Exception("User not logged in, login to continue.")

    data = await call("/exam/exam_result.php", addtional_headers={"Cookie": sessions[session_id].cookie})
    sp = BeautifulSoup(data, "html.parser")

    return [option["value"].strip()[:-1] for option in sp.find_all("option")]


async def get_result(ctx: Context, exam_code: str) -> dict:
    session_id = ctx.session_id
    if sessions.get(session_id) is None:
        raise Exception("User not logged in, login to continue.")


    data = await call("/exam/exam_result.php", addtional_headers={"Cookie": sessions[session_id].cookie})
    sp = BeautifulSoup(data, "html.parser")
    exam_codes = {option["value"].strip()[:-1]: option["value"].strip()[-1] for option in sp.find_all("option")}
    
    if exam_code not in exam_codes.keys():
        raise Exception(f"Invalid exam code {exam_code}. Available valid exam codes: {", ".join(exam_codes.keys())}")
    
    table = sp.find("div", id=f"div_{exam_codes[exam_code]}")

    rows = table.find_all("tr", class_="row1")
    data = [
        [
            td.get_text(strip=True).replace("$", "") 
            for td in row.find_all("td", class_="tablecol2")
        ]
        for row in rows
    ]

    return {
        "semester": data[0][0],
        "papers": {sub[1]: sub[2:] for sub in data}
    }
