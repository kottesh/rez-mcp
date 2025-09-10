from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
import logging
import httpx
from config import rez_config
from pydantic import BaseModel

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
    password: str


sessions: dict[str, SessionData] = {}

app = FastAPI()


@app.get("/")
async def root() -> str:
    return "Rez MCP Server"


@app.get("/auth/login")
async def login_page(session_id: str | None = None) -> HTMLResponse:
    if session_id is None or session_id not in sessions:
        return HTMLResponse(content="Invalid Session", status_code=400)

    if session_id in sessions and sessions[session_id] is not None:
        if sessions[session_id].expiresAt < datetime.now():
            del sessions[session_id]
            return HTMLResponse(content="Session expired!", status_code=200)

        return HTMLResponse(content="You are already logged in!", status_code=200)

    return templates.TemplateResponse(
        "login.html", {"request": {}, "session_id": session_id}
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
        follow_redirects=True,
        verify=False,
    ) as client:
        print(creds)
        try:
            response = client.post(
                "/login.php?action=process",
                data={"user_name": creds.username, "pass_word": creds.password},
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            response.raise_for_status()
            print(response.text)
            if "student login" in response.text.lower():
                raise HTTPException(
                    detail="Incorrect username or password", status_code=401
                )

            cookie = response.headers.get("set-cookie", "").split(";")[0].strip()
            sessions[session_id] = SessionData(session_id=session_id, cookie=cookie)

            return JSONResponse(content={"message": "Login Ok!"}, status_code=200)

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code if e.response else "Unknown status"
            content = e.response.text if e.response else "Unknown error"

            logger.error(f"HTTPError: ({status_code}) - {content}")
            return JSONResponse(content={"error": f"{content}"}, status_code=500)

        except Exception as e:
            logger.error(f"Error during API call: {str(e)}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
