from fastmcp import Context
import logging
from utils import call
from tools.utils import get_session
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO
import re
from config import rez_config

logger = logging.getLogger(__name__)


async def get_results(ctx: Context) -> list:
    """
    Retrieves a list of available semester exam result codes from the CIT Results Site.

    Returns:
        list: A list of the available exam result codes.

    Raises:
        Exception: If the user is not logged in or if the API call fails.
    """

    session = get_session(ctx)
    data = await call(
        "/exam/exam_result.php",
        addtional_headers={"Cookie": session.cookie},
    )
    sp = BeautifulSoup(data, "html.parser")

    return [option["value"].strip()[:-1] for option in sp.find_all("option")]


async def get_result(ctx: Context, exam_code: str) -> dict:
    """
    Retrieves the exam result using the `exam_code`.

    Command:
        Show the results in a markdown table format.

    Returns:
        dict: A python dictionary that cotains the fields such as GPA, Semesters, Papers(Name, Grade, Pass/Fail)

    Raises:
        Exception: If the user is not logged in or if the API call fails.
    """

    session = get_session(ctx)
    data = await call(
        "/exam/exam_result.php",
        addtional_headers={"Cookie": session.cookie},
    )
    sp = BeautifulSoup(data, "html.parser")
    exam_codes = {
        option["value"].strip()[:-1]: option["value"].strip()[-1]
        for option in sp.find_all("option")
    }

    if exam_code not in exam_codes.keys():
        raise Exception(
            f"Invalid exam code {exam_code}. Available valid exam codes: {', '.join(exam_codes.keys())}"
        )

    table = sp.find("div", id=f"div_{exam_codes[exam_code]}")

    rows = table.find_all("tr", class_="row1")
    data = [
        [
            td.get_text(strip=True).replace("$", "")
            for td in row.find_all("td", class_="tablecol2")
        ]
        for row in rows
    ]

    pdf = await call(
        "/exam/result.php",
        {"exam_cd": exam_code},
        addtional_headers={"Cookie": session.cookie},
        return_bytes=True,
    )
    gpa = re.search(
        r"GPA for (.*?) Semester\s*:\s*(.*)",
        PdfReader(BytesIO(pdf)).get_page(0).extract_text(),
    ).group(2)

    return {
        "semester": data[0][0],
        "papers": {sub[1]: sub[2:] for sub in data},
        "gpa": gpa,
    }


async def download_result(ctx: Context, exam_code: str) -> str:
    """
    Generates the result PDF by `exam_code`

    Returns
        str: Result PDF downloadable link

    Raises:
        Exception: If the user is not logged in.
    """

    session = get_session(ctx)
    return f"[Click here to download result]({rez_config.rez_base_url}/pdf/result?session_id={session.session_id}&exam_code={exam_code})"
