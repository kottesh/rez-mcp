from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
import logging
import httpx
from config import rez_config
from pydantic import BaseModel, SecretStr
import re

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")


class SessionData:
    def __init__(self, session_id: str, cookie: str):
        self.session_id: str = session_id
        self.cookie: str = cookie
        self.createdAt: datetime = datetime.now()
        self.expiresAt: datetime = datetime.now() + timedelta(hours=1)


class LoginCreds(BaseModel):
    username: str
    password: SecretStr


sessions: dict[str, SessionData] = {}

app = FastAPI()


@app.get("/")
async def root() -> str:
    return "Rez MCP Server"


@app.get("/auth/login")
async def login_page(request: Request, session_id: str | None = None) -> HTMLResponse:
    if session_id is None or session_id not in sessions:
        return HTMLResponse(content="Invalid Session", status_code=400)

    session = sessions.get(session_id)
    if session:
        if session.expiresAt < datetime.now():
            del sessions[session_id]
            return HTMLResponse(content="Session expired!", status_code=200)

        return HTMLResponse(content="You are already logged in!", status_code=200)

    return templates.TemplateResponse(
        request=request, name="login.html", context={"session_id": session_id}
    )


@app.post("/auth/login")
async def authorize(session_id: str, creds: LoginCreds) -> JSONResponse:
    if session_id not in sessions:
        logger.error(f"Invalid session Id {session_id} during authorization")
        return JSONResponse(
            content={"error": f"Invalid session Id {session_id}"}, status_code=400
        )

    with httpx.Client(
        base_url=rez_config.cit_base_url,
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
                logger.warning(f"Login failed, received 200 OK. Body: {response.text}")
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

            sessions[session_id] = SessionData(session_id=session_id, cookie=cookie)

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
