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
from data import sessions, blacklist_tokens

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="src/templates")


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


async def session_cleanup():
    while True:
        try:
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

        except asyncio.CancelledError:
            break


async def remove_blacklist_tokens():
    while True:
        try:
            blacklist_len = len(blacklist_tokens)

            if blacklist_len == 0:
                logger.info("No blacklisted tokens to clean up.")
            else:
                logger.info(f"Cleaning {blacklist_len} blacklisted tokens")
                blacklist_tokens.clear()

            await asyncio.sleep(600)  # sleep for 10 minutes

        except asyncio.CancelledError:
            break


@asynccontextmanager
async def rez_lifespan(app):
    blacklist_cleanup_task = asyncio.create_task(remove_blacklist_tokens())
    session_cleanup_task = asyncio.create_task(session_cleanup())

    yield

    blacklist_cleanup_task.cancel()
    session_cleanup_task.cancel()


rez_app = FastAPI()


@rez_app.get("/")
async def root() -> str:
    return "Rez MCP Server"


@rez_app.get("/auth/login")
async def login_page(request: Request, token: str) -> HTMLResponse:
    if token in blacklist_tokens or not verify_token(token)[1]:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "status_code": "401",
                "error_title": "Oh ohhhhh!",
                "error_message": "Login link expired or its invalid. Please request a new login to continue.",
            },
        )

    return templates.TemplateResponse(
        request=request, name="login.html", context={"token": token}
    )


@rez_app.post("/auth/login")
async def authorize(request: Request, token: str, creds: LoginCreds) -> JSONResponse:
    if token in blacklist_tokens:
        raise HTTPException(detail="Token is no longer valid", status_code=401)

    data, valid = verify_token(token)
    if not valid:
        raise HTTPException(detail=data, status_code=401)


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
            blacklist_tokens.add(token)

            set_cookie_header = response.headers.get("set-cookie")
            if not set_cookie_header:
                logger.error("No set-cookie header found in the response.")
                raise HTTPException(
                    detail="Login failed: no session cookie received.", status_code=500
                )

            cookie_match = re.match(r"([^;]+)", set_cookie_header)
            if not cookie_match:
                logger.error(f"Could not parse cookie from header: {set_cookie_header}")
                raise HTTPException(
                    detail="Login failed: could not parse session cookie.",
                    status_code=500,
                )

            cookie = cookie_match.group(1).strip()

            sessions[session_id] = SessionData(
                roll_no=creds.username, session_id=session_id, cookie=cookie
            )

            return JSONResponse(content={"message": "Login Ok!"}, status_code=200)

        except HTTPException as e:
            raise e
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            content = e.response.text
            logger.error(f"HTTP Status Error: ({status_code}) - {content}")
            raise HTTPException(
                detail="Auth service returned an error", status_code=502
            )
        except httpx.RequestError as e:
            logger.error(f"HTTP Request Error: {str(e)}")
            raise HTTPException(
                detail="Couldn't reach the authentication service", status_code=503
            )
        except Exception as e:
            logger.error(f"An unexpected error occurred during authorization: {str(e)}")
            raise HTTPException(
                detail="An unexpected internal error occurred.", status_code=500
            )


@rez_app.get("/pdf/result")
async def generate_result(request: Request, token: str) -> StreamingResponse:
    data, valid = verify_token(token)

    if not valid:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "status_code": "410",
                "error_title": "Oh ohhhhh!",
                "error_message": "The link is invalid or its expired, Please request a new one.",
            },
        )

    session_id, exam_code = data.split(":")
    session = sessions.get(session_id)

    if not session:
        logger.info(
            f"No session found with ID {session_id}. May be the user logged out."
        )
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "status_code": "401",
                "error_title": "Are you logged in ?",
                "error_message": "Oops! Your session decided to take a catnap. Time to log back in and wake it up!",
            },
        )

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
async def generate_hallticket(request: Request, token: str) -> StreamingResponse:
    data, valid = verify_token(token)

    if not valid:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "status_code": "410",
                "error_title": "Oh ohhhhh!",
                "error_message": "The link is invalid or its expired, Please request a new one.",
            },
        )

    session_id, exam_code = data.split(":")
    session = sessions.get(session_id)

    if not session:
        logger.info(
            f"No session found with ID {session_id}. May be the user logged out."
        )
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "status_code": "401",
                "error_title": "Are you logged in ?",
                "error_message": "Oops! Your session decided to take a catnap. Time to log back in and wake it up!",
            },
        )

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
