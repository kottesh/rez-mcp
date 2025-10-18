from datetime import datetime, timedelta


class SessionData:
    def __init__(self, roll_no: str, session_id: str, cookie: str):
        self.register_no: str = roll_no
        self.session_id: str = session_id
        self.cookie: str = cookie
        self.createdAt: datetime = datetime.now()
        self.expiresAt: datetime = datetime.now() + timedelta(minutes=15)


sessions: dict[str, SessionData] = {}
blacklist_tokens: set[str] = set()
