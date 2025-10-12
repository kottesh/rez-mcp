from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
import logging
import httpx
from config import REZConfig
from pydantic import BaseModel, SecretStr
import re
from utils import call
from io import BytesIO
import asyncio
from contextlib import asynccontextmanager
from signer import verify_token

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")


class SessionData:
    def __init__(self, roll_no: str, session_id: str, cookie: str):
        self.register_no: str = roll_no
        self.session_id: str = session_id
        self.cookie: str = cookie
        self.createdAt: datetime = datetime.now()
        self.expiresAt: datetime = datetime.now() + timedelta(minutes=15)


class LoginCreds(BaseModel):
    username: str
    password: SecretStr


sessions: dict[str, SessionData] = {}


async def session_cleanup():
    while True:
        now = datetime.now()
        logger.info(f"Running regular cleanup at {now}")
        expired = [
            sid for sid, data in sessions.items() if data and now > data.expiresAt
        ]

        if expired:
            for sid in expired:
                del sessions[sid]
            logger.info(f"Cleaned up {len(expired)} sessions.")
        else:
            logger.info("No expired sessions to be cleaned up.")

        await asyncio.sleep(600)  # sleep for 10 minutes


@asynccontextmanager
async def rez_lifespan(app):
    task = asyncio.create_task(session_cleanup())
    yield
    task.cancel()


rez_app = FastAPI()


@rez_app.get("/")
async def root() -> str:
    return "Rez MCP Server"


@rez_app.get("/auth/login")
async def login_page(request: Request, token: str | None = None) -> HTMLResponse:
    data, valid = verify_token(token)

    if not valid:
        return HTMLResponse(content=data, status_code=401)

    session_id = data
    session = sessions.get(session_id)

    if session:
        if datetime.now() > session.expiresAt:
            del sessions[session_id]
            return HTMLResponse(content="Session expired!", status_code=200)

        return HTMLResponse(content="You are already logged in!", status_code=200)

    return templates.TemplateResponse(
        request=request, name="login.html", context={"token": token}
    )


@rez_app.post("/auth/login")
async def authorize(token: str, creds: LoginCreds) -> JSONResponse:
    data, valid = verify_token(token)

    if not valid:
        return HTMLResponse(content=data, status_code=401)

    session_id = data

    with httpx.Client(
        base_url=REZConfig.CIT_BASE_URL,
        timeout=15.0,
        follow_redirects=False,
        verify=False,
    ) as client:
        try:
            response = client.post(
                "/login.php?action=process",
                data={
                    "user_name": creds.username,
                    "pass_word": creds.password.get_secret_value(),
                },
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

            # A successful login will result in a 302 redirect.
            # If we get a 200 OK, it means the login page was re-rendered,
            # likely with an error message.
            if response.status_code == 200:
                logger.warning("Login failed, received 200 OK. Body")
                if "student login" in response.text.lower():
                    raise HTTPException(
                        detail="Incorrect username or password", status_code=401
                    )
                else:
                    raise HTTPException(
                        detail="Login failed: Unexpected response from auth service.",
                        status_code=500,
                    )

            if response.status_code != 302:
                response.raise_for_status()

            logger.info(f"Login successful with redirect. Headers: {response.headers}")

            set_cookie_header = response.headers.get("set-cookie")
            if not set_cookie_header:
                logger.error("No set-cookie header found in the response.")
                return JSONResponse(
                    content={"error": "Login failed: no session cookie received."},
                    status_code=500,
                )

            cookie_match = re.match(r"([^;]+)", set_cookie_header)
            if not cookie_match:
                logger.error(f"Could not parse cookie from header: {set_cookie_header}")
                return JSONResponse(
                    content={"error": "Login failed: could not parse session cookie."},
                    status_code=500,
                )
            cookie = cookie_match.group(1).strip()

            sessions[session_id] = SessionData(
                roll_no=creds.username, session_id=session_id, cookie=cookie
            )

            return JSONResponse(content={"message": "Login Ok!"}, status_code=200)

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            content = e.response.text
            logger.error(f"HTTP Status Error: ({status_code}) - {content}")
            return JSONResponse(
                content={"error": f"An external service error occurred: {status_code}"},
                status_code=502,
            )
        except httpx.RequestError as e:
            logger.error(f"HTTP Request Error: {str(e)}")
            return JSONResponse(
                content={"error": "Could not connect to the authentication service."},
                status_code=504,
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred during authorization: {str(e)}")
            return JSONResponse(
                content={"error": "An unexpected internal error occurred."},
                status_code=500,
            )


@rez_app.get("/pdf/result")
async def generate_result(token: str) -> StreamingResponse:
    data, valid = verify_token(token)

    if not valid:
        return HTMLResponse(content=data, status_code=401)

    session_id, exam_code = data.split(":")
    session = sessions.get(session_id)

    if not session:
        logger.info(
            f"No session found with ID {session_id}. May be the user logged out."
        )
        return HTMLResponse(content="Are you logged in ?", status_code=401)

    register_no = session.register_no.replace(" ", "")
    cookie = session.cookie
    result_pdf = await call(
        "/exam/result.php",
        {"exam_cd": exam_code},
        addtional_headers={"Cookie": cookie},
        return_bytes=True,
    )
    result_pdf = BytesIO(result_pdf)

    return StreamingResponse(
        result_pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=RESULT_{register_no}_{exam_code}.pdf"
        },
    )


@rez_app.get("/pdf/hallticket")
async def generate_hallticket(token: str) -> StreamingResponse:
    data, valid = verify_token(token)

    if not valid:
        return HTMLResponse(content=data, status_code=401)

    session_id, exam_code = data.split(":")
    session = sessions.get(session_id)

    if not session:
        logger.info(
            f"No session found with ID {session_id}. May be the user logged out."
        )
        return HTMLResponse(content="Are you logged in ?", status_code=401)

    register_no = session.register_no.replace(" ", "")
    cookie = session.cookie
    result_pdf = await call(
        "/exam/rpt_exam_hallticket.php",
        {"exam_cd": exam_code},
        addtional_headers={"Cookie": cookie},
        return_bytes=True,
    )
    result_pdf = BytesIO(result_pdf)

    return StreamingResponse(
        result_pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=HT_{register_no}_{exam_code}.pdf"
        },
    )
