import hmac
import hashlib
from config import REZConfig
import time
import base64
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


def generate_token(data: str, expiry_in: int = 600) -> str:
    expiry = int(time.time()) + expiry_in

    payload = f"{data}|{expiry}"

    signature = hmac.new(
        REZConfig.SECRET_KEY, payload.encode(), hashlib.sha256
    ).hexdigest()

    return base64.urlsafe_b64encode(f"{payload}.{signature}".encode()).decode()


def verify_token(token: str) -> Tuple[str, bool]:
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()

        payload, signature = decoded.rsplit(".", 1)

        expected_sig = hmac.new(
            REZConfig.SECRET_KEY, payload.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return "Invalid token", False

        data, expiry = payload.rsplit("|", 1)

        if int(time.time()) > int(expiry):
            return "Token expired", False

        return data, True

    except Exception as e:
        logger.error(f"Failed to verify the token: {str(e)}")

        return "Failed to verify the token", False
