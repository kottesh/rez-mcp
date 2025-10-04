from manager import sessions, SessionData
from fastmcp import Context


def get_session(ctx: Context) -> SessionData:
    session_id = ctx.session_id

    if session_id not in sessions:
        raise Exception("You are not logged in, Please login to continue!")

    return sessions[session_id]
